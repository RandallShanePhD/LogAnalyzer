import chromadb
from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction
import ollama

# Initialize same collection and embedding function
chroma_client = chromadb.PersistentClient(path="./chroma_db")
clip_ef = OpenCLIPEmbeddingFunction(
    model_name="ViT-B-32", checkpoint="laion2b_s34b_b79k"
)
collection = chroma_client.get_collection(
    name="multimodal_knowledge", embedding_function=clip_ef
)


def query_flight_assistant(question: str):
    # Retrieve top 3 items across text, pdf, and images
    results = collection.query(query_texts=[question], n_results=3)

    retrieved_docs = results["documents"][0]
    metadatas = results["metadatas"][0]

    context_str = ""
    referenced_images = []

    for doc, meta in zip(retrieved_docs, metadatas):
        if meta["type"] == "image":
            referenced_images.append(meta["file_path"])
            context_str += f"\n[Referenced Diagram/Image: {meta['source']}]\n"
        else:
            context_str += f"\n[Source: {meta['source']}]\n{doc}\n"

    # Send retrieved context to local Llama 3.2 via Ollama
    prompt = f"""You are an expert paragliding coach. Use the context below to answer the pilot's question.

Context:
{context_str}

Question: {question}
Answer:"""

    response = ollama.generate(model="llama3.2", prompt=prompt)

    print(f"\n--- Answer ---\n{response['response']}")
    if referenced_images:
        print(f"\n📷 Related Diagrams Found: {referenced_images}")


if __name__ == "__main__":
    user_query = "How should I handle thermalling in strong wind drift?"
    query_flight_assistant(user_query)