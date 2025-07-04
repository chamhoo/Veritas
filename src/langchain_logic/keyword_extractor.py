"""
Analyzes user requests and extracts key search terms.
"""

# Keyword extractor logic.
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import config

def get_keyword_extractor_chain():
    """
    Creates a LangChain chain that extracts concise, searchable keywords
    from a user's natural language request.
    """
    llm = ChatOpenAI(api_key=config.OPENAI_API_KEY, model="gpt-3.5-turbo", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert at extracting concise, search-engine-friendly keywords from user text. "
                   "Provide a short list of 3-5 keywords or phrases, separated by commas. Do not use any introductory text."),
        ("user", "{user_request}")
    ])
    
    chain = prompt | llm | StrOutputParser()
    
    return chain

async def extract_keywords(user_request: str) -> str:
    """
    Asynchronously extracts keywords from a user's request.
    
    Args:
        user_request: The natural language request from the user.
        
    Returns:
        A comma-separated string of keywords.
    """
    chain = get_keyword_extractor_chain()
    keywords = await chain.ainvoke({"user_request": user_request})
    return keywords.strip()