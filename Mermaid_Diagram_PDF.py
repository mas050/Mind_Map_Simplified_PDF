import streamlit as st
from streamlit.components.v1 import html
import google.generativeai as genai
import os
from pdf2image import convert_from_path
import base64
from PIL import Image
import io
import tempfile
from PyPDF2 import PdfReader
import requests

# Securely set API keys (replace placeholders securely in production)
API_KEY = os.getenv("GENAI_API_KEY", "AIzaSyCOhsh-JWBd6B006GA0UgdIW6wRcNon7lk")

# Configure Generative AI
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")


def clean_text(text):
    """Removes specific unwanted characters."""
    return text.replace("(", "").replace(")", "")


def pdf_to_images_in_memory(pdf_file):
    """Converts a PDF to a list of images."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(pdf_file.read())
        temp_pdf.close()
        images = convert_from_path(temp_pdf.name)
    os.unlink(temp_pdf.name)
    return images


def extract_text_from_pdf(pdf_file):
    """Extracts text from a PDF."""
    reader = PdfReader(pdf_file)
    return "".join(page.extract_text() for page in reader.pages)

def render_mermaid_with_kroki(mermaid_code):
    """Render Mermaid diagram using kroki.io with custom styles for better visibility."""
    # Add Mermaid configuration for white background and custom styles
    theme_config = """
    %%{init: {'theme': 'neutral', 'themeVariables': {
        'primaryColor': '#ffffff',
        'primaryTextColor': '#000000',
        'primaryBorderColor': '#000000',
        'lineColor': '#000000',
        'arrowheadColor': '#000000',
        'fontFamily': 'Arial'
    }}}%%
    """
    mermaid_code = theme_config + "\n" + mermaid_code

    url = "https://kroki.io/mermaid/png"
    response = requests.post(url, data=mermaid_code.encode('utf-8'))
    if response.status_code == 200:
        return base64.b64encode(response.content).decode('utf-8')
    else:
        raise Exception(f"Error rendering diagram: {response.status_code} - {response.text}")

def display_mermaid_image_kroki(mermaid_code):
    """Display Mermaid diagram using Kroki."""
    try:
        img_base64 = render_mermaid_with_kroki(mermaid_code)
        zoomable_html = f"""
        <html>
        <head>
            <style>
                img {{
                    width: 100%;
                    height: auto;
                    transform: scale(1);
                    transition: transform 0.2s;
                }}
                img:hover {{
                    transform: scale(2);
                }}
            </style>
        </head>
        <body>
            <img src="data:image/png;base64,{img_base64}" alt="Diagram" />
        </body>
        </html>
        """
        html(zoomable_html, height=800)
    except Exception as e:
        st.error(f"Error displaying Mermaid diagram: {e}")


def generate_mind_map_text(text):
    """Generates summarized text and Mermaid diagram from a document."""
    summarizer_prompt = f"""
    Extract the key concepts, ideas, and insights a reader should retain after reading the document.
    Regroup them by type of concepts or ideas that fit together.
    Ignore any content related to the structure or formatting of the document. 
    Focus exclusively on the core concepts that would interest the reader. 
    For each core concept, provide detailed insights, including any relevant statistics, facts, numbers, or references mentioned. 
    Ensure the summary is comprehensive and structured, highlighting all significant details that add depth to the core concepts.

    Text to summarize: 
    {text}
    """
    summary = model.generate_content(summarizer_prompt).text

    diagram_prompt = f"""
    I want to create a comprehensive Mermaid diagram from a document. \
    The diagram should represent the document's structure, key concepts, and interconnections. \
    Please ensure the output is in Mermaid syntax and follows this structure: \

    Hierarchy and Structure:

    Use a root node to represent the overall topic or document title.
    Create main branches for primary sections of the document.
    Add sub-branches for subsections and break down detailed points as leaf nodes.

    Contextual Details:

    For each leaf node (end of a branch), add a separate node connected to it that includes a brief summary or explanation of its significance. \
    These should serve as supporting explanations for someone unfamiliar with the content. \

    Styling and Formatting:

    Use different styles to visually distinguish node levels:
    Root node: prominent and central.
    Main sections: second-level branches.
    Subsections: third-level branches.
    Contextual explanation nodes: separate, with lighter styling.
    Flow and Connectivity:

    Ensure nodes are logically connected to reflect the document flow of information.
    Include line breaks (<br>) or concise bullet-style text in the nodes where appropriate for readability.
    Output Requirements:

    Provide clean and structured Mermaid syntax.
    Ensure that the final diagram:
    Is hierarchical and tree-like.
    Highlights interconnections.
    Includes explanation nodes for context.

    Use and follow exactly the format as a structural reference for your output: \
        
    graph TD
        %% Root Node
        A[Root Topic or Document Title]

        %% Subgraph 1
        subgraph SG1[Main Section 1]
            B1[Subsection 1.1]
            B1 --> Context_B1[Context: Brief explanation or significance of Subsection 1.1.]
            B2[Subsection 1.2]
            B2 --> Context_B2[Context: Brief explanation or significance of Subsection 1.2.]
        end
        A --> SG1

    Here's the document to analyze: \
    {summary}
    """
    return model.generate_content(diagram_prompt).text


def extract_mermaid_code(raw_diagram):
    """Cleans and extracts Mermaid diagram syntax."""
    clean_prompt = f"""
    From this mermaid diagram structure generated by a LLM, extract the mermaid diagram piece and output just that and nothing else. \
    
    Output requirements:
    -Do not output explanations, introduction, conclusion of special characters. \
    -Do not add Triple backticks or asterisk or quotation mark or any special characters \
    -It has to start with "graph " followed by the rest of the mermaid diagram structure \
    Here's the diagram structure to extract: \
    {raw_diagram}
    """
    return model.generate_content(clean_prompt).text


# Streamlit app
def main():
    st.title("Mind Map Generator on Document")
    uploaded_files = st.file_uploader("Upload PDF files", type=["pdf"], accept_multiple_files=True)

    if uploaded_files:
        combined_text = ""
        for file in uploaded_files:
            combined_text += extract_text_from_pdf(file) + "\n"

        if combined_text.strip():
            with st.spinner("Generating mind map..."):
                try:
                    raw_diagram = generate_mind_map_text(combined_text)
                    mermaid_code = extract_mermaid_code(raw_diagram)
                    cleaned_code = clean_text(mermaid_code)

                    st.subheader("Generated Mermaid Diagram:")
                    display_mermaid_image_kroki(cleaned_code)
                except Exception as e:
                    st.error(f"Error generating Mermaid diagram: {e}")
    else:
        st.warning("Please upload a PDF file to proceed.")


if __name__ == "__main__":
    main()
