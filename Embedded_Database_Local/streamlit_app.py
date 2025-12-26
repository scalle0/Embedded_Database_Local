"""Streamlit web interface for document search."""

import streamlit as st
from pathlib import Path
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from query_interface import QueryInterface


# Page configuration
st.set_page_config(
    page_title="Document Search System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .quote-box {
        background-color: #f0f2f6;
        border-left: 4px solid #4CAF50;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .context-text {
        color: #666;
        font-style: italic;
    }
    .quote-text {
        font-weight: bold;
        color: #000;
    }
    .metadata-box {
        background-color: #e8f4f8;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .score-badge {
        background-color: #4CAF50;
        color: white;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_query_interface():
    """Initialize query interface (cached)."""
    return QueryInterface()


def format_score(score: float) -> str:
    """Format similarity score as percentage."""
    return f"{score * 100:.1f}%"


def display_quote(quote_data: dict, query: str):
    """Display a quote with context in a nice format."""
    if not quote_data:
        return

    context_before = quote_data.get('context_before', '')
    quote_text = quote_data.get('quote', '')
    context_after = quote_data.get('context_after', '')

    # Highlight query terms
    qi = st.session_state.query_interface

    quote_html = f"""
    <div class="quote-box">
        <span class="context-text">{context_before}</span>
        <span class="quote-text">{quote_text}</span>
        <span class="context-text">{context_after}</span>
    </div>
    """

    st.markdown(quote_html, unsafe_allow_html=True)


def display_result(result: dict, index: int, query: str, show_full: bool = False):
    """Display a single search result."""
    with st.container():
        # Header with score
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            source = result['metadata'].get('source_file', 'Unknown')
            filename = Path(source).name if source != 'Unknown' else source
            st.markdown(f"### 📄 {filename}")

        with col2:
            score = result['score']
            st.markdown(
                f'<span class="score-badge">Match: {format_score(score)}</span>',
                unsafe_allow_html=True
            )

        with col3:
            file_type = result['metadata'].get('file_type', 'unknown')
            st.badge(file_type.upper(), type="secondary")

        # Metadata
        metadata = result['metadata']
        meta_cols = st.columns(4)

        with meta_cols[0]:
            if 'created_date' in metadata:
                st.caption(f"📅 Created: {metadata['created_date'][:10]}")

        with meta_cols[1]:
            if 'chunk_index' in metadata:
                st.caption(f"📑 Chunk: {metadata['chunk_index']}")

        with meta_cols[2]:
            if 'ocr_confidence' in metadata:
                st.caption(f"🔍 OCR: {metadata['ocr_confidence']:.0f}%")

        with meta_cols[3]:
            if 'char_count' in metadata:
                st.caption(f"📊 Length: {metadata['char_count']} chars")

        st.divider()

        # Show best quote or full text
        if 'best_quote' in result and result['best_quote'] and not show_full:
            st.markdown("**📌 Most Relevant Quote:**")
            display_quote(result['best_quote'], query)

            # Button to show more quotes
            with st.expander("📝 See more quotes and full text"):
                if 'quotes' in result and len(result['quotes']) > 1:
                    st.markdown("**Other relevant quotes:**")
                    for i, quote in enumerate(result['quotes'][1:], 2):
                        st.markdown(f"*Quote {i}:*")
                        display_quote(quote, query)
                        st.markdown("")

                st.markdown("**Full Chunk Text:**")
                st.text_area(
                    "Full text",
                    result['text'],
                    height=200,
                    key=f"full_text_{result['id']}"
                )

        else:
            # Show full text
            st.markdown("**Full Text:**")
            st.text_area(
                "Full text",
                result['text'],
                height=200,
                key=f"full_text_{result['id']}"
            )

        # Button to view full document
        if st.button(f"📖 View Full Document", key=f"view_doc_{result['id']}"):
            st.session_state.selected_document = result['metadata'].get('source_file')
            st.session_state.page = 'document_viewer'
            st.rerun()

        st.markdown("---")


def search_page():
    """Main search page."""
    st.title("🔍 Document Search System")

    # Initialize query interface
    if 'query_interface' not in st.session_state:
        with st.spinner("Initializing search system..."):
            st.session_state.query_interface = initialize_query_interface()

    qi = st.session_state.query_interface

    # Get database stats
    stats = qi.get_statistics()

    # Sidebar with filters and settings
    with st.sidebar:
        st.header("📊 Database Statistics")
        st.metric("Total Chunks", stats.get('total_chunks', 0))
        st.metric("Unique Documents", stats.get('unique_sources', 0))

        st.divider()

        st.header("⚙️ Search Settings")

        # Number of results
        n_results = st.slider(
            "Number of results",
            min_value=1,
            max_value=50,
            value=10,
            help="Maximum number of results to return"
        )

        # Similarity threshold
        min_similarity = st.slider(
            "Minimum similarity",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.05,
            help="Only show results with similarity above this threshold"
        )

        st.divider()

        st.header("🔧 Filters")

        # File type filter
        file_type_filter = st.selectbox(
            "File Type",
            ["All", "pdf", "docx", "image", "enex", "eml", "txt"],
            help="Filter by document type"
        )

        # Date filter (optional)
        use_date_filter = st.checkbox("Filter by date")
        date_filter = None
        if use_date_filter:
            date_filter = st.date_input("Created after")

        st.divider()

        # Display options
        st.header("📋 Display Options")
        show_quotes = st.checkbox("Extract quotes", value=True)
        context_chars = st.slider(
            "Context characters",
            min_value=50,
            max_value=500,
            value=200,
            help="Characters before/after quote for context"
        )

    # Main search interface
    query = st.text_input(
        "Enter your search query:",
        placeholder="e.g., medical records from 2023, handwritten notes about Diana...",
        help="Enter a natural language search query"
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)
    with col2:
        if st.button("🗑️ Clear Results", use_container_width=True):
            if 'results' in st.session_state:
                del st.session_state.results

    # Perform search
    if search_button and query:
        with st.spinner("Searching..."):
            # Build filters
            filters = {}
            if file_type_filter != "All":
                filters['file_type'] = file_type_filter

            # Search
            results = qi.search(
                query=query,
                n_results=n_results,
                filters=filters if filters else None,
                min_similarity=min_similarity
            )

            # Extract quotes if enabled
            if show_quotes and results:
                results = qi.extract_quotes(query, results, context_chars)

            st.session_state.results = results
            st.session_state.query = query

    # Display results
    if 'results' in st.session_state and st.session_state.results:
        results = st.session_state.results
        query = st.session_state.get('query', '')

        st.success(f"Found {len(results)} results")

        # Display each result
        for i, result in enumerate(results, 1):
            display_result(result, i, query, show_full=not show_quotes)

    elif 'results' in st.session_state:
        st.warning("No results found. Try adjusting your query or filters.")


def document_viewer_page():
    """Page to view full document."""
    st.title("📖 Document Viewer")

    if st.button("← Back to Search"):
        st.session_state.page = 'search'
        st.rerun()

    if 'selected_document' not in st.session_state:
        st.warning("No document selected.")
        return

    source_file = st.session_state.selected_document
    qi = st.session_state.query_interface

    st.header(f"📄 {Path(source_file).name}")

    with st.spinner("Loading document..."):
        # Get all chunks
        chunks = qi.get_document_chunks(source_file)

        if not chunks:
            st.error("No chunks found for this document.")
            return

        # Display metadata
        metadata = chunks[0]['metadata']

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Source", metadata.get('file_type', 'Unknown').upper())
        with col2:
            if 'created_date' in metadata:
                st.metric("Created", metadata['created_date'][:10])
        with col3:
            st.metric("Chunks", len(chunks))

        st.divider()

        # Display full document
        full_text = qi.get_full_document(source_file)

        # Search within document
        search_in_doc = st.text_input("🔍 Search within this document:")

        if search_in_doc:
            highlighted = qi.highlight_text(full_text, search_in_doc)
            st.markdown(highlighted)
        else:
            st.text_area("Full Document", full_text, height=600)

        # Show chunks
        with st.expander(f"📑 View Individual Chunks ({len(chunks)} total)"):
            for i, chunk in enumerate(chunks):
                st.markdown(f"**Chunk {i + 1}** (Index: {chunk['metadata'].get('chunk_index', 'N/A')})")
                st.text_area(
                    f"chunk_{i}",
                    chunk['text'],
                    height=150,
                    key=f"chunk_display_{i}",
                    label_visibility="collapsed"
                )


def main():
    """Main application entry point."""
    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = 'search'

    # Route to appropriate page
    if st.session_state.page == 'search':
        search_page()
    elif st.session_state.page == 'document_viewer':
        document_viewer_page()


if __name__ == "__main__":
    main()
