"""
Uses an LLM to perform semantic comparison and filter retrieved content.
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import config
import logging

logger = logging.getLogger(__name__)

def get_relevance_filter_chain():
    """
    Creates a LangChain chain that determines if a piece of content is relevant
    to an original user request.
    """
    llm = ChatOpenAI(api_key=config.OPENAI_API_KEY, model="gpt-3.5-turbo", temperature=0)
    
    prompt = ChatPromptTemplate.from_template(
        """
        Original user request: "{original_request}"
        
        Content to analyze:
        ---
        Title: {content_title}
        Snippet: {content_snippet}
        ---
        
        Is the content snippet highly relevant to the original user request? 
        Answer with only "Yes" or "No".
        """
    )
    
    chain = prompt | llm | StrOutputParser()
    
    return chain

async def is_content_relevant(original_request: str, content_title: str, content_snippet: str) -> bool:
    """
    Uses an LLM to perform a semantic check for relevance.
    
    Args:
        original_request: The user's initial detailed request.
        content_title: The title of the found item (e.g., article title).
        content_snippet: A summary or snippet of the found item.
        
    Returns:
        True if the content is deemed relevant, False otherwise.
    """
    chain = get_relevance_filter_chain()
    try:
        response = await chain.ainvoke({
            "original_request": original_request,
            "content_title": content_title,
            "content_snippet": content_snippet
        })
        
        # Normalize the response to handle potential whitespace or case issues
        return response.strip().lower() == 'yes'
    except Exception as e:
        logger.error(f"Error during relevance check: {e}")
        # Default to False in case of an LLM error to avoid pushing irrelevant content
        return False