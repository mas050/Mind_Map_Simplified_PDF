import streamlit as st
from streamlit.components.v1 import html
import google.generativeai as genai
import os
from pdf2image import convert_from_path
import base64
from PIL import Image
import io
import tempfile
from groq import Groq
from playwright.sync_api import sync_playwright
from PyPDF2 import PdfReader

from playwright._impl._driver import compute_driver_executable

def ensure_playwright_browsers_installed():
    """Ensures that Playwright browser binaries are installed."""
    try:
        from playwright.__main__ import main as playwright_main
        print("Checking Playwright browser installation...")
        playwright_main(["install", "chromium"])  # Only install Chromium for your use case
    except Exception as e:
        print(f"Error installing Playwright browsers: {e}")

# Ensure browsers are installed before using Playwright
ensure_playwright_browsers_installed()


# Securely set API keys (replace placeholders securely in production)
API_KEY = os.getenv("GENAI_API_KEY", "AIzaSyCOhsh-JWBd6B006GA0UgdIW6wRcNon7lk")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")

# Configure Generative AI and Groq
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
client = Groq(api_key=GROQ_API_KEY)


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


def render_high_res_mermaid(mermaid_code, output_file, width=1920, height=1080, scale=5):
    """Renders a high-resolution Mermaid diagram using Playwright."""
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <script>
            mermaid.initialize({{"startOnLoad": true}});
        </script>
    </head>
    <body>
        <div class="mermaid">{mermaid_code}</div>
    </body>
    </html>
    """

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": width * scale, "height": height * scale})
        page = context.new_page()
        page.set_content(html_template)
        page.screenshot(path=output_file, full_page=True)
        browser.close()
    return output_file


def display_zoomable_image(image_path):
    """Displays an image with zoom functionality in Streamlit."""
    with open(image_path, "rb") as img_file:
        img_base64 = base64.b64encode(img_file.read()).decode("utf-8")
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
        <img src="data:image/png;base64,{img_base64}" alt="Zoomable Image" />
    </body>
    </html>
    """
    html(zoomable_html, height=800)


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

    Use and follow exactlty the format as a structural reference for your output: \
    To name the subgraph, inside the brakets do not start the name by a number. \
        
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

        %% Subgraph 2
        subgraph SG2[Main Section 2]
            C1[Subsection 2.1]
            C1 --> Context_C1[Context: Brief explanation or significance of Subsection 2.1.]
            C2[Subsection 2.2]
            C2 --> Context_C2[Context: Brief explanation or significance of Subsection 2.2.]
        end
        A --> SG2

    Consistency with the Document:

    Break down the document ensuring all sections and their relationships are clearly represented.
    Do not get lost with useless information.
    Provide the Mermaid diagram syntax as the final output, and ensure it follows these guidelines.

    Here is the document to analyze: \
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
    -It has to start with "graph " followed by the rest of the ermaid diagram structure \
    -Just output the mermaid text because it will be passed to a playwright python script to render it as an image, so it needs to be only the mermaid diagram structure. \
    
    Treatment required of the mermaid diagram structure:\
    -remove any Triple backticks or asterisk or quotation mark in it \
    -If you notice a piece of text with parenthesis, remove it! For exemple, if you see "this is (text) to treat" you would completely remove it and output "this is to treat" \
    -remove any section related to image, logo or irrelevant piece that are not about key concepts, ideas and insights a reader should remember after reading the document. \

    Use and follow exactlty the format as a structural reference for your output: \
    To name the subgraph, inside the brakets do not start the name by a number. \

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

        %% Subgraph 2
        subgraph SG2[Main Section 2]
            C1[Subsection 2.1]
            C1 --> Context_C1[Context: Brief explanation or significance of Subsection 2.1.]
            C2[Subsection 2.2]
            C2 --> Context_C2[Context: Brief explanation or significance of Subsection 2.2.]
        end
        A --> SG2

    Here's the piece of text to extract the mermaid diagram structure: \
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

                    output_file = "diagram.png"
                    render_high_res_mermaid(cleaned_code, output_file)

                    st.subheader("Generated Mermaid Diagram:")
                    display_zoomable_image(output_file)
                except Exception as e:
                    st.error(f"Error generating Mermaid diagram: {e}")
    else:
        st.warning("Please upload a PDF file to proceed.")


if __name__ == "__main__":
    main()
