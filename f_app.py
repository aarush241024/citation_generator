import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import xml.etree.ElementTree as ET

def extract_doi_metadata(doi):
    """Extract metadata using CrossRef API"""
    try:
        headers = {'Accept': 'application/json'}
        response = requests.get(f'https://api.crossref.org/works/{doi}', headers=headers)
        data = response.json()['message']
        metadata = {
            'title': data.get('title', [''])[0],
            'authors': [f"{author.get('given', '')} {author.get('family', '')}"
                       for author in data.get('author', [])],
            'year': str(data.get('published-print', {}).get('date-parts', [['']])[0][0]),
            'month': 'December',  # Default month if not available
            'journal': data.get('container-title', [''])[0],
            'volume': data.get('volume', ''),
            'issue': data.get('issue', ''),
            'doi': doi,
            'url': f"https://doi.org/{doi}",
            'publisher': data.get('publisher', '')
        }
        return metadata
    except:
        return None

def extract_arxiv_metadata(arxiv_id):
    """Extract metadata from arXiv API"""
    try:
        api_url = f'http://export.arxiv.org/api/query?id_list={arxiv_id}'
        response = requests.get(api_url)
        root = ET.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entry = root.find('atom:entry', ns)
        if entry is not None:
            metadata = {
                'title': entry.find('atom:title', ns).text.strip(),
                'authors': [author.find('atom:name', ns).text
                           for author in entry.findall('atom:author', ns)],
                'year': entry.find('atom:published', ns).text[:4],
                'month': datetime.strptime(entry.find('atom:published', ns).text[:10],
                                          '%Y-%m-%d').strftime('%B'),
                'url': f"https://arxiv.org/abs/{arxiv_id}",
                'journal': 'arXiv',
                'publisher': 'Cornell University'
            }
            return metadata
    except:
        return None

def extract_general_metadata(url):
    """Extract metadata from general webpage using meta tags"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        metadata = {
            'title': '',
            'authors': [],
            'year': str(datetime.now().year),
            'month': datetime.now().strftime('%B'),
            'journal': '',
            'volume': '',
            'issue': '',
            'publisher': '',
            'url': url
        }
        # Try various meta tags for title
        title_tag = (
            soup.find('meta', property='og:title') or
            soup.find('meta', property='dc:title') or
            soup.find('meta', {'name': 'citation_title'})
        )
        if title_tag:
            metadata['title'] = title_tag.get('content', '')
        elif soup.title:
            metadata['title'] = soup.title.string

        # Try various meta tags for author
        author_tags = soup.find_all('meta', {'name': 'citation_author'})
        if author_tags:
            metadata['authors'] = [tag.get('content', '') for tag in author_tags]
        else:
            author_tag = (
                soup.find('meta', {'name': 'author'}) or
                soup.find('meta', property='article:author')
            )
            if author_tag:
                metadata['authors'] = [author_tag.get('content', '')]

        # Try to get date information
        date_tag = (
            soup.find('meta', {'name': 'citation_publication_date'}) or
            soup.find('meta', property='article:published_time')
        )
        if date_tag:
            date_str = date_tag.get('content', '')
            try:
                date = datetime.fromisoformat(date_str.split('T')[0])
                metadata['year'] = str(date.year)
                metadata['month'] = date.strftime('%B')
            except:
                pass

        # Try to get journal information
        journal_tag = soup.find('meta', {'name': 'citation_journal_title'})
        if journal_tag:
            metadata['journal'] = journal_tag.get('content', '')

        # Try to get volume and issue
        volume_tag = soup.find('meta', {'name': 'citation_volume'})
        if volume_tag:
            metadata['volume'] = volume_tag.get('content', '')
        issue_tag = soup.find('meta', {'name': 'citation_issue'})
        if issue_tag:
            metadata['issue'] = issue_tag.get('content', '')

        return metadata
    except:
        return None

def identify_url_type(url):
    """Identify the type of URL and extract appropriate metadata"""
    # Check for DOI
    doi_match = re.search(r'10\.\d{4,}/[-._;()/:\w]+', url)
    if doi_match or 'doi.org' in url:
        doi = doi_match.group(0) if doi_match else url.split('doi.org/')[-1]
        metadata = extract_doi_metadata(doi)
        if metadata:
            return metadata

    # Check for arXiv
    arxiv_match = re.search(r'arxiv.org/(?:abs|pdf)/(\d+\.\d+)', url)
    if arxiv_match:
        metadata = extract_arxiv_metadata(arxiv_match.group(1))
        if metadata:
            return metadata

    # Try general metadata extraction
    return extract_general_metadata(url)

def format_apa_citation(metadata):
    """Format citation in APA style"""
    if not metadata or not metadata.get('title'):
        return "Unable to generate citation."

    # Format authors
    authors = metadata.get('authors', [])
    if len(authors) > 1:
        formatted_authors = [f"{a.split()[-1]}, {'. '.join(n[0] for n in a.split()[:-1])}."
                           for a in authors]
        author_text = ", ".join(formatted_authors[:-1]) + ", & " + formatted_authors[-1]
    elif authors:
        author = authors[0].split()
        author_text = f"{author[-1]}, {'. '.join(n[0] for n in author[:-1])}."
    else:
        author_text = ""

    # Build citation
    citation = f"{author_text} ({metadata.get('year', '')}"
    if metadata.get('month'):
        citation += f", {metadata['month']}"
    citation += f"). {metadata['title']}"

    if metadata.get('journal'):
        citation += f". {metadata['journal']}"
        if metadata.get('volume'):
            citation += f", {metadata['volume']}"
            if metadata.get('issue'):
                citation += f"({metadata['issue']})"

    if metadata.get('doi'):
        citation += f". https://doi.org/{metadata['doi']}"
    elif metadata.get('url'):
        citation += f". {metadata['url']}"

    return citation

def format_chicago_citation(metadata):
    """Format citation in Chicago style"""
    if not metadata or not metadata.get('title'):
        return "Unable to generate citation."

    # Format authors
    authors = metadata.get('authors', [])
    if len(authors) > 1:
        author_text = ", ".join(authors[:-1]) + ", and " + authors[-1]
    elif authors:
        author_text = authors[0]
    else:
        author_text = ""

    # Build citation
    citation = f'{author_text}. "{metadata["title"]}"'
    
    if metadata.get('journal'):
        citation += f'. {metadata["journal"]}'
        if metadata.get('volume'):
            citation += f' {metadata["volume"]}'
            if metadata.get('issue'):
                citation += f', no. {metadata["issue"]}'
    
    if metadata.get('month') and metadata.get('year'):
        citation += f' {metadata["month"]} {metadata["year"]}.'
    elif metadata.get('year'):
        citation += f' {metadata["year"]}.'
        
    if metadata.get('doi'):
        citation += f' https://doi.org/{metadata["doi"]}.'
    elif metadata.get('url'):
        citation += f' {metadata["url"]}.'

    return citation

def format_mla_citation(metadata):
    """Format citation in MLA style"""
    if not metadata or not metadata.get('title'):
        return "Unable to generate citation."

    # Format authors
    authors = metadata.get('authors', [])
    if authors:
        if len(authors) > 1:
            author_text = f"{authors[0]}, et al"
        else:
            author_text = authors[0]
    else:
        author_text = ""

    # Build citation
    citation = f'{author_text}. "{metadata["title"]}"'

    if metadata.get('journal'):
        citation += f'. {metadata["journal"]}'
        if metadata.get('volume') and metadata.get('issue'):
            citation += f', vol. {metadata["volume"]}, no. {metadata["issue"]}'

    if metadata.get('publisher'):
        citation += f', {metadata["publisher"]}'

    if metadata.get('month') and metadata.get('year'):
        citation += f', {metadata["month"][:3]}. {metadata["year"]}'

    if metadata.get('doi'):
        citation += f'. Crossref, https://doi.org/{metadata["doi"]}'
    elif metadata.get('url'):
        citation += f'. {metadata["url"]}'

    citation += '.'
    return citation

def main():
    # Remove styling
    st.markdown("""
        <style>
        .stButton button {display: none;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stTextInput > label {display: none;}
        .stSelectbox > label {display: none;}
        </style>
    """, unsafe_allow_html=True)

    url = st.text_input("", placeholder="Enter URL")
    style = st.selectbox("", ["APA", "Chicago", "MLA"])

    if url:
        metadata = identify_url_type(url)
        if metadata:
            # Show style header
            if style == "APA":
                st.write("American Psychological Association Style")
            elif style == "Chicago":
                st.write("Chicago Style")
            else:
                st.write("Modern Language Association Style")

            # Generate citation
            if style == "APA":
                citation = format_apa_citation(metadata)
            elif style == "Chicago":
                citation = format_chicago_citation(metadata)
            else:
                citation = format_mla_citation(metadata)

            # Display citation
            st.text(citation)

            # Add copy button
            if st.button("Copy Citation"):
                pass

if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="Citation Generator")
    main()