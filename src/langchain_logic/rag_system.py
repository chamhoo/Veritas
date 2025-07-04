"""
Implements the Retrieval-Augmented Generation (RAG) system for learning from user feedback.
"""

import faiss
from langchain.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from langchain.docstore.in_memory import InMemoryDocstore
from langchain.retrievers import TimeWeightedVectorStoreRetriever
from typing import List
import logging
from config import config

logger = logging.getLogger(__name__)

# This dictionary will store a RAG retriever for each information request (channel).
# In a production system, you might persist this or use a more robust storage solution.
rag_retrievers = {}

def get_or_create_rag_retriever(request_id: int):
    """
    Initializes and returns a RAG retriever for a specific info request.
    This retriever uses a time-weighted vector store to prioritize recent feedback.
    """
    if request_id in rag_retrievers:
        return rag_retrievers[request_id]

    logger.info(f"Creating new RAG retriever for request ID {request_id}")
    
    # Use OpenAI for embeddings
    embeddings = OpenAIEmbeddings(api_key=config.OPENAI_API_KEY)
    
    # Initialize a FAISS vector store
    embedding_size = 1536  # OpenAI embeddings dimensionality
    index = faiss.IndexFlatL2(embedding_size)
    vectorstore = FAISS(embeddings.embed_query, index, InMemoryDocstore({}), {})

    # Create the Time-Weighted Retriever
    retriever = TimeWeightedVectorStoreRetriever(
        vectorstore=vectorstore,
        decay_rate=0.01, # How quickly the importance of old memories decay
        k=1 # Number of feedback documents to retrieve
    )
    
    rag_retrievers[request_id] = retriever
    return retriever

def add_feedback_to_rag(request_id: int, content: str, is_relevant: bool):
    """
    Adds user feedback to the appropriate RAG retriever.
    The feedback is stored as a Document with metadata indicating relevance.
    
    Args:
        request_id: The ID of the info request this feedback applies to.
        content: The text content of the item that received feedback.
        is_relevant: True if the user marked it as relevant (👍), False otherwise (👎).
    """
    retriever = get_or_create_rag_retriever(request_id)
    
    # The metadata helps us understand the feedback later
    metadata = {"relevant": is_relevant}
    
    # Add the content as a document to the retriever's memory
    retriever.add_documents([Document(page_content=content, metadata=metadata)])
    logger.info(f"Added feedback to RAG for request {request_id}. Relevant: {is_relevant}")

async def get_rag_feedback_summary(request_id: int, content_to_check: str) -> str:
    """
    Retrieves the most similar past feedback from the RAG system.
    This can be used to augment the relevance filtering decision.
    
    Args:
        request_id: The ID of the info request.
        content_to_check: The new content being considered.
        
    Returns:
        A summary of past feedback on similar content, or an empty string if none exists.
    """
    if request_id not in rag_retrievers:
        return "" # No feedback system initiated for this request yet.

    retriever = rag_retrievers[request_id]
    try:
        # Find the most similar past feedback document
        similar_docs = await retriever.aget_relevant_documents(content_to_check)
        
        if not similar_docs:
            return ""
        
        # Create a summary string from the most similar past feedback
        feedback_doc = similar_docs[0]
        was_relevant = feedback_doc.metadata.get("relevant", False)
        relevance_str = "was marked as RELEVANT" if was_relevant else "was marked as IRRELEVANT"
        
        summary = f"User feedback on similar past content: This content {relevance_str}."
        logger.info(f"RAG summary for request {request_id}: {summary}")
        return summary

    except Exception as e:
        logger.error(f"Error retrieving from RAG system for request {request_id}: {e}")
        return ""
