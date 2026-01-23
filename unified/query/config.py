"""
Sample unified query configurations.

These queries can be applied to both HackerNews and arXiv articles.
Categories are only used when filtering arXiv papers.
"""

from .query import Query, QueryCollection


# Sample unified query configurations
UNIFIED_QUERIES = {
    "ai": Query(
        name="AI & Machine Learning",
        description="Articles about artificial intelligence, machine learning, LLMs, and related topics",
        terms=[
            '"artificial intelligence"',
            '"machine learning"',
            '"deep learning"',
            '"neural network"',
            '"LLM"',
            '"large language model"',
            '"GPT"',
            '"Claude"',
            '"ChatGPT"',
            '"OpenAI"',
            '"Anthropic"',
            '"AI agents"',
            '"transformer"',
            '"diffusion model"',
        ],
        categories=["cs.AI", "cs.CL", "cs.LG"],
    ),

    "agentic_ai": Query(
        name="Agentic AI",
        description="Papers related to AI agents, autonomous systems, and LLM-based agents",
        terms=[
            '"agentic AI"',
            '"AI agents"',
            '"autonomous agents"',
            '"LLM agents"',
            '"language model agents"',
            '"agent systems"',
            '"multi-agent systems" AND "language models"',
            '"tool-using agents"',
            '"reasoning agents"',
        ],
        categories=["cs.AI", "cs.CL", "cs.LG", "cs.MA"],
    ),

    "security": Query(
        name="Security & Hacking",
        description="Articles about cybersecurity, hacking, vulnerabilities, and data breaches",
        terms=[
            '"cybersecurity"',
            '"data breach"',
            '"vulnerability"',
            '"exploit"',
            '"malware"',
            '"ransomware"',
            '"zero-day"',
            '"CVE-"',
            '"hacking"',
            '"penetration testing"',
            '"security flaw"',
            '"encryption"',
        ],
        categories=["cs.CR"],
    ),

    "cryptography": Query(
        name="Cryptography",
        description="Papers related to cryptography, encryption, and security protocols",
        terms=[
            '"cryptography"',
            '"encryption"',
            '"public key"',
            '"blockchain"',
            '"cryptographic protocols"',
            '"zero-knowledge proofs"',
            '"homomorphic encryption"',
            '"post-quantum cryptography"',
            '"secure multi-party computation"',
        ],
        categories=["cs.CR", "cs.IT", "math.IT"],
    ),

    "programming": Query(
        name="Programming",
        description="Articles about programming languages, tools, and software development",
        terms=[
            '"programming language"',
            '"software development"',
            '"open source"',
            '"rust" AND "programming"',
            '"python" AND ("library" OR "framework")',
            '"javascript"',
            '"typescript"',
            '"golang"',
            '"compiler"',
            '"developer tools"',
        ],
        categories=["cs.PL", "cs.SE"],
    ),

    "databases": Query(
        name="Databases",
        description="Articles about databases, SQL, and data storage",
        terms=[
            '"database"',
            '"SQL"',
            '"PostgreSQL"',
            '"MySQL"',
            '"MongoDB"',
            '"Redis"',
            '"SQLite"',
            '"NoSQL"',
            '"data warehouse"',
            '"query optimization"',
        ],
        categories=["cs.DB"],
    ),

    "robotics": Query(
        name="Robotics",
        description="Papers related to robotics, robot learning, and embodied AI",
        terms=[
            '"robotics"',
            '"robot learning"',
            '"robotic manipulation"',
            '"humanoid robots"',
            '"autonomous robots"',
            '"robot perception"',
            '"embodied AI"',
            '"robot control"',
            '"mobile robots"',
        ],
        categories=["cs.RO", "cs.AI", "cs.CV", "cs.LG"],
    ),
}


def get_default_collection() -> QueryCollection:
    """
    Get the default query collection with all predefined queries.

    Returns:
        QueryCollection with all unified queries
    """
    collection = QueryCollection()
    for query_id, query in UNIFIED_QUERIES.items():
        collection.add(query_id, query)
    return collection


def get_query(query_id: str) -> Query:
    """
    Get a predefined query by ID.

    Args:
        query_id: Query identifier

    Returns:
        Query instance

    Raises:
        KeyError: If query_id not found
    """
    if query_id not in UNIFIED_QUERIES:
        available = list(UNIFIED_QUERIES.keys())
        raise KeyError(f"Query '{query_id}' not found. Available: {available}")
    return UNIFIED_QUERIES[query_id]


def list_available_queries() -> list:
    """Get list of available query IDs."""
    return list(UNIFIED_QUERIES.keys())
