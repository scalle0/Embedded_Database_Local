"""Example script demonstrating programmatic usage of the document processing system."""

from pathlib import Path
from query_interface import QueryInterface
from main import process_documents


def example_1_process_single_file():
    """Example: Process a single document."""
    print("=" * 80)
    print("Example 1: Process Single Document")
    print("=" * 80)

    # Process a specific file
    stats = process_documents(
        input_path="data/input/sample.pdf",
        parallel=False  # Use sequential for single file
    )

    print(f"\nProcessed {stats['ingestion']['processed']} documents")
    print(f"Database now contains {stats['database_totals']['total_chunks']} chunks")


def example_2_batch_process():
    """Example: Batch process all documents in a directory."""
    print("\n" + "=" * 80)
    print("Example 2: Batch Process Directory")
    print("=" * 80)

    # Process all files in input directory with parallel processing
    stats = process_documents(
        input_path="data/input",
        parallel=True  # Enable parallel processing
    )

    print(f"\nProcessing complete!")
    print(f"Successfully processed: {stats['database']['processed']}")
    print(f"Failed: {stats['database']['failed']}")
    print(f"Skipped: {stats['database']['skipped']}")


def example_3_semantic_search():
    """Example: Perform semantic search."""
    print("\n" + "=" * 80)
    print("Example 3: Semantic Search")
    print("=" * 80)

    # Initialize query interface
    qi = QueryInterface()

    # Search for medical records
    query = "medical examination reports from 2023"
    results = qi.search(query, n_results=5)

    print(f"\nQuery: '{query}'")
    print(f"Found {len(results)} results:\n")

    for i, result in enumerate(results, 1):
        print(f"[{i}] Score: {result['score']:.3f}")
        print(f"    Source: {result['metadata'].get('source_file', 'Unknown')}")

        # Show snippet
        text = result['text']
        snippet = text[:150] + "..." if len(text) > 150 else text
        print(f"    Preview: {snippet}\n")


def example_4_metadata_filtering():
    """Example: Search with metadata filters."""
    print("\n" + "=" * 80)
    print("Example 4: Metadata Filtering")
    print("=" * 80)

    qi = QueryInterface()

    # Search only in PDF files
    results = qi.search(
        query="correspondence",
        n_results=10,
        filters={'file_type': 'pdf'}  # Only PDFs
    )

    print(f"Found {len(results)} results in PDF files")


def example_5_get_document_chunks():
    """Example: Retrieve all chunks from a specific document."""
    print("\n" + "=" * 80)
    print("Example 5: Get Document Chunks")
    print("=" * 80)

    qi = QueryInterface()

    # Get all chunks from a specific file
    source_file = "data/input/sample.pdf"
    chunks = qi.get_document_chunks(source_file)

    print(f"Document: {source_file}")
    print(f"Total chunks: {len(chunks)}\n")

    for i, chunk in enumerate(chunks[:3], 1):  # Show first 3
        print(f"Chunk {i}:")
        print(f"  Index: {chunk['metadata'].get('chunk_index', 'N/A')}")
        print(f"  Chars: {chunk['metadata'].get('char_count', 'N/A')}")
        print(f"  Preview: {chunk['text'][:100]}...\n")


def example_6_database_stats():
    """Example: Get database statistics."""
    print("\n" + "=" * 80)
    print("Example 6: Database Statistics")
    print("=" * 80)

    qi = QueryInterface()
    stats = qi.get_statistics()

    print(f"Database Statistics:")
    print(f"  Total chunks: {stats.get('total_chunks', 0)}")
    print(f"  Unique sources: {stats.get('unique_sources', 0)}")
    print(f"  Collection: {stats.get('collection_name', 'N/A')}")


def example_7_custom_query():
    """Example: Advanced query with custom parameters."""
    print("\n" + "=" * 80)
    print("Example 7: Advanced Query")
    print("=" * 80)

    qi = QueryInterface()

    # Search with multiple filters and minimum similarity
    results = qi.search(
        query="handwritten notes",
        n_results=20,
        filters={
            'file_type': 'image',  # Only images
        },
        min_similarity=0.75  # Only highly relevant results
    )

    print(f"Found {len(results)} highly relevant results (>75% similarity)")

    for result in results:
        print(f"  - {result['metadata'].get('filename', 'Unknown')}: "
              f"{result['score']:.1%} match")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("DOCUMENT PROCESSING SYSTEM - EXAMPLE USAGE")
    print("=" * 80)

    # Note: Comment out processing examples if you don't want to reprocess
    # example_1_process_single_file()
    # example_2_batch_process()

    # Query examples (require existing database)
    try:
        example_3_semantic_search()
        example_4_metadata_filtering()
        example_5_get_document_chunks()
        example_6_database_stats()
        example_7_custom_query()

    except Exception as e:
        print(f"\nNote: Some examples require processed documents in the database.")
        print(f"Run 'python main.py' first to process documents.")
        print(f"\nError: {e}")

    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
