import os
import chromadb
from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter
from PIL import Image
from pypdf import PdfReader

# 1. Initialize ChromaDB with OpenCLIP
# OpenCLIP generates synchronized embeddings for BOTH text and image pixels
chroma_client = chromadb.PersistentClient(path="./chroma_db")
clip_ef = OpenCLIPEmbeddingFunction(
    model_name="ViT-B-32", checkpoint="laion2b_s34b_b79k"
)

collection = chroma_client.get_or_create_collection(
    name="multimodal_knowledge", embedding_function=clip_ef
)


# --- HELPERS FOR PROCESSING ---


def process_txt(file_path: str):
    """Reads and chunks standard text files."""
    print(f"📄 Processing Text: {os.path.basename(file_path)}")
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=150
    )
    chunks = splitter.split_text(text)

    filename = os.path.basename(file_path)
    for i, chunk in enumerate(chunks):
        collection.add(
            ids=[f"txt_{filename}_chunk_{i}"],
            documents=[chunk],  # CLIP embeds the text string
            metadatas=[
                {
                    "source": filename,
                    "type": "text",
                    "file_path": file_path,
                }
            ],
        )
    print(f"  └─ Ingested {len(chunks)} text chunks.")


def process_pdf(file_path: str):
    """Extracts page text from PDFs and chunks it."""
    print(f"📚 Processing PDF: {os.path.basename(file_path)}")
    reader = PdfReader(file_path)
    full_text = []

    for idx, page in enumerate(reader.pages):
        content = page.extract_text()
        if content:
            full_text.append(f"\n--- Page {idx + 1} ---\n{content}")

    combined_text = "\n".join(full_text)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=150
    )
    chunks = splitter.split_text(combined_text)

    filename = os.path.basename(file_path)
    for i, chunk in enumerate(chunks):
        collection.add(
            ids=[f"pdf_{filename}_chunk_{i}"],
            documents=[chunk],  # CLIP embeds the text string
            metadatas=[
                {
                    "source": filename,
                    "type": "pdf",
                    "file_path": file_path,
                }
            ],
        )
    print(f"  └─ Ingested {len(chunks)} PDF text chunks.")


def process_image(file_path: str):
    """Embeds raw images directly using CLIP's vision encoder."""
    print(f"🖼️  Processing Image: {os.path.basename(file_path)}")
    filename = os.path.basename(file_path)

    try:
        # Load image via PIL
        img = Image.open(file_path)

        # OpenCLIPEmbeddingFunction directly accepts a PIL Image or numpy array
        # We pass image data to images=[] instead of documents=[]
        collection.add(
            ids=[f"img_{filename}"],
            images=[img],  # CLIP embeds raw pixels
            documents=[
                f"Visual Diagram/Photo file: {filename}"
            ],  # Fallback text description
            metadatas=[
                {"source": filename, "type": "image", "file_path": file_path}
            ],
        )
        print("  └─ Successfully embedded image vector with CLIP.")
    except Exception as e:
        print(f"  └─ Error processing image {filename}: {e}")


# --- MAIN INGESTION ROUTINE ---


def ingest_directory(directory_path: str):
    if not os.path.exists(directory_path):
        print(f"Directory {directory_path} does not exist.")
        return

    for filename in os.listdir(directory_path):
        filepath = os.path.join(directory_path, filename)
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".txt":
            process_txt(filepath)
        elif ext == ".pdf":
            process_pdf(filepath)
        elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
            process_image(filepath)


if __name__ == "__main__":
    data_folder = "./data"
    print("Starting Multimodal Ingestion Pipeline...\n")
    ingest_directory(data_folder)
    print("\n✅ Ingestion complete! Total items stored:", collection.count())