"""Query interface for searching the embedded database."""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.config_loader import get_config
from utils.logger import Logger
from agents.database_agent import DatabaseAgent


class QueryInterface:
    """Interface for querying the vector database."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize query interface.

        Args:
            config_path: Optional path to config file
        """
        # Load configuration
        self.config = get_config(config_path)
        self.config.validate()

        # Setup logging
        log_config = self.config.get('logging', {})
        self.logger = Logger.get_logger(__name__, log_config)

        # Initialize Gemini for embedding queries
        self._init_gemini()

        # Initialize database agent
        self.db_agent = DatabaseAgent(self.config.get_all(), self.logger)

        self.logger.info("Query interface initialized")

    def _init_gemini(self):
        """Initialize Gemini for query embedding."""
        try:
            import google.generativeai as genai

            gemini_config = self.config.get('gemini', {})
            api_key = gemini_config.get('api_key')

            if not api_key or api_key.startswith('${'):
                raise ValueError("Gemini API key not configured")

            genai.configure(api_key=api_key)

            self.embedding_model = gemini_config.get(
                'embedding_model',
                'models/text-embedding-004'
            )
            self.genai = genai

            self.logger.info(f"Gemini initialized for queries: {self.embedding_model}")

        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini for queries: {e}")

    def search(
        self,
        query: str,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Search the database with a text query.

        Args:
            query: Search query text
            n_results: Maximum number of results to return
            filters: Metadata filters (e.g., {'file_type': 'pdf'})
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of search results with text, metadata, and scores
        """
        self.logger.info(f"Searching for: '{query}'")

        # Generate embedding for query
        query_embedding = self._embed_query(query)

        # Query database
        query_config = self.config.get('query', {})
        max_k = min(n_results, query_config.get('max_top_k', 50))

        results = self.db_agent.query(
            query_embedding=query_embedding,
            n_results=max_k,
            where=filters
        )

        # Format results
        formatted_results = self._format_results(results, min_similarity)

        self.logger.info(f"Found {len(formatted_results)} results")

        return formatted_results

    def search_by_metadata(
        self,
        filters: Dict[str, Any],
        n_results: int = 100
    ) -> List[Dict[str, Any]]:
        """Search by metadata only (no semantic search).

        Args:
            filters: Metadata filters
            n_results: Maximum number of results

        Returns:
            List of matching documents
        """
        self.logger.info(f"Searching by metadata: {filters}")

        # Get documents matching filter
        results = self.db_agent.collection.get(
            where=filters,
            limit=n_results,
            include=['documents', 'metadatas']
        )

        formatted = []
        for i, doc_id in enumerate(results['ids']):
            formatted.append({
                'id': doc_id,
                'text': results['documents'][i],
                'metadata': results['metadatas'][i],
                'score': 1.0  # No similarity score for metadata-only search
            })

        self.logger.info(f"Found {len(formatted)} results")

        return formatted

    def _embed_query(self, query: str) -> List[float]:
        """Generate embedding for query text.

        Args:
            query: Query text

        Returns:
            Embedding vector
        """
        try:
            result = self.genai.embed_content(
                model=self.embedding_model,
                content=query,
                task_type="retrieval_query"  # Different from document embedding
            )

            embedding = result['embedding']
            self.logger.debug(f"Generated query embedding (dim: {len(embedding)})")

            return embedding

        except Exception as e:
            self.logger.error(f"Failed to embed query: {e}")
            raise

    def _format_results(
        self,
        results: Dict[str, Any],
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Format ChromaDB results.

        Args:
            results: Raw ChromaDB results
            min_similarity: Minimum similarity threshold

        Returns:
            Formatted results list
        """
        formatted = []

        if not results['ids'] or not results['ids'][0]:
            return formatted

        for i, doc_id in enumerate(results['ids'][0]):
            # Convert distance to similarity score
            distance = results['distances'][0][i]
            similarity = 1 - distance  # For cosine distance

            # Filter by minimum similarity
            if similarity < min_similarity:
                continue

            formatted.append({
                'id': doc_id,
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'score': similarity,
                'distance': distance
            })

        # Sort by score (highest first)
        formatted.sort(key=lambda x: x['score'], reverse=True)

        return formatted

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary with database statistics
        """
        return self.db_agent.get_stats()

    def get_document_chunks(self, source_file: str) -> List[Dict[str, Any]]:
        """Get all chunks from a specific source document.

        Args:
            source_file: Source file path

        Returns:
            List of chunks from that document
        """
        results = self.db_agent.collection.get(
            where={'source_file': source_file},
            include=['documents', 'metadatas']
        )

        formatted = []
        for i, doc_id in enumerate(results['ids']):
            formatted.append({
                'id': doc_id,
                'text': results['documents'][i],
                'metadata': results['metadatas'][i],
            })

        # Sort by chunk_index
        formatted.sort(key=lambda x: x['metadata'].get('chunk_index', 0))

        return formatted

    def extract_quotes(
        self,
        query: str,
        results: List[Dict[str, Any]],
        context_chars: int = 200
    ) -> List[Dict[str, Any]]:
        """Extract exact quotes from search results with context.

        Args:
            query: Original search query
            results: Search results from search()
            context_chars: Number of characters before/after for context

        Returns:
            Results enhanced with quotes and context
        """
        import re

        enhanced_results = []

        for result in results:
            text = result['text']

            # Find potential quote matches (keyword-based)
            query_words = set(re.findall(r'\w+', query.lower()))

            # Score sentences by keyword overlap
            sentences = re.split(r'(?<=[.!?])\s+', text)
            quote_candidates = []

            for sentence in sentences:
                sentence_words = set(re.findall(r'\w+', sentence.lower()))
                overlap = len(query_words & sentence_words)

                if overlap > 0:
                    quote_candidates.append({
                        'sentence': sentence,
                        'overlap': overlap,
                        'position': text.find(sentence)
                    })

            # Sort by keyword overlap
            quote_candidates.sort(key=lambda x: x['overlap'], reverse=True)

            # Get top quote with context
            quotes = []
            for candidate in quote_candidates[:3]:  # Top 3 quotes
                pos = candidate['position']
                sentence = candidate['sentence']

                # Extract context
                start = max(0, pos - context_chars)
                end = min(len(text), pos + len(sentence) + context_chars)

                context_before = text[start:pos]
                context_after = text[pos + len(sentence):end]

                quotes.append({
                    'quote': sentence,
                    'context_before': context_before,
                    'context_after': context_after,
                    'full_context': context_before + sentence + context_after,
                    'relevance': candidate['overlap']
                })

            # Add quotes to result
            result_copy = result.copy()
            result_copy['quotes'] = quotes
            result_copy['best_quote'] = quotes[0] if quotes else None

            enhanced_results.append(result_copy)

        return enhanced_results

    def get_full_document(self, source_file: str) -> str:
        """Reconstruct full document from all chunks.

        Args:
            source_file: Source file path

        Returns:
            Full document text
        """
        chunks = self.get_document_chunks(source_file)

        # Concatenate all chunks in order
        full_text = '\n\n'.join(chunk['text'] for chunk in chunks)

        return full_text

    def highlight_text(
        self,
        text: str,
        query: str,
        highlight_format: str = "**{}**"
    ) -> str:
        """Highlight query terms in text.

        Args:
            text: Text to highlight
            query: Search query
            highlight_format: Format string for highlighting (default: markdown bold)

        Returns:
            Text with highlighted terms
        """
        import re

        # Extract query words
        query_words = re.findall(r'\w+', query.lower())

        # Highlight each word
        highlighted = text
        for word in query_words:
            if len(word) > 2:  # Skip very short words
                pattern = re.compile(r'\b(' + re.escape(word) + r')\b', re.IGNORECASE)
                highlighted = pattern.sub(lambda m: highlight_format.format(m.group(1)), highlighted)

        return highlighted


def interactive_search():
    """Run interactive search CLI."""
    print("=" * 80)
    print("Document Search Interface")
    print("=" * 80)

    try:
        query_interface = QueryInterface()

        # Show database stats
        stats = query_interface.get_statistics()
        print(f"\nDatabase contains:")
        print(f"  - {stats.get('total_chunks', 0)} chunks")
        print(f"  - {stats.get('unique_sources', 0)} unique source documents")
        print()

        while True:
            print("-" * 80)
            query = input("Enter search query (or 'quit' to exit): ").strip()

            if query.lower() in {'quit', 'exit', 'q'}:
                break

            if not query:
                continue

            try:
                # Get number of results
                n_results_input = input("Number of results (default 10): ").strip()
                n_results = int(n_results_input) if n_results_input else 10

                # Perform search
                results = query_interface.search(query, n_results=n_results)

                # Display results
                print(f"\nFound {len(results)} results:\n")

                for i, result in enumerate(results, 1):
                    print(f"[{i}] Score: {result['score']:.3f}")
                    print(f"    Source: {result['metadata'].get('source_file', 'Unknown')}")
                    print(f"    Type: {result['metadata'].get('file_type', 'Unknown')}")

                    # Show snippet
                    text = result['text']
                    snippet = text[:200] + "..." if len(text) > 200 else text
                    print(f"    Text: {snippet}")
                    print()

                # Option to see full text
                detail = input("See full text for result number (or press Enter to skip): ").strip()
                if detail.isdigit():
                    idx = int(detail) - 1
                    if 0 <= idx < len(results):
                        print("\n" + "=" * 80)
                        print(f"Full text of result {detail}:")
                        print("=" * 80)
                        print(results[idx]['text'])
                        print("=" * 80)
                        print(f"Metadata: {results[idx]['metadata']}")
                        print("=" * 80)

            except Exception as e:
                print(f"Error during search: {e}")

    except Exception as e:
        print(f"Failed to initialize query interface: {e}")
        return

    print("\nGoodbye!")


if __name__ == "__main__":
    interactive_search()
