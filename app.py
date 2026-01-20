# app.py (for Streamlit Cloud deployment)
import streamlit as st
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import pandas as pd
# from groq import Groq

# Cấu hình Gemini API từ secrets
os.environ['GOOGLE_API_KEY'] = st.secrets['GOOGLE_API_KEY']
# os.environ['GROQ_API_KEY'] = st.secrets['GROQ_API_KEY']
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])

# Load data từ CSV (file phải upload lên GitHub repo cùng app.py)
@st.cache_data
def load_data():
    data_df = pd.read_csv('data_mock.csv')  # Giả sử file ở cùng thư mục
    return data_df

data_df = load_data()

# Tạo documents và metadata
@st.cache_data
def create_docs_and_metadata(df):
    documents = [
        f"{row['Source']} {row['Relation']} {row['Target']}: {row['Evidence']}"
        for _, row in df.iterrows()
    ]
    metadata = [
        {"access_level": row['Access_Level'], "verified": row['Status'] in ['Attested', 'Verified']}
        for _, row in df.iterrows()
    ]
    return documents, metadata

documents, metadata = create_docs_and_metadata(data_df)

# Load embedding model và tạo embeddings/index (cache để tối ưu)
@st.cache_resource
def load_embedder_and_index(docs):
    embedder = SentenceTransformer('paraphrase-mpnet-base-v2')
    doc_embeddings = embedder.encode(docs)
    dimension = doc_embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(doc_embeddings).astype('float32'))
    return embedder, doc_embeddings, index

embedder, doc_embeddings, index = load_embedder_and_index(documents)

# Gatekeeper filter (dựa role)
def gatekeeper_filter(user_role):
    if user_role == "Owner":
        return list(range(len(documents)))  # All
    elif user_role == "Recruiter":
        return [i for i, m in enumerate(metadata) if m["access_level"] in ["attested", "public"]]
    else:  # Anonymous
        return [i for i, m in enumerate(metadata) if m["access_level"] == "public"]

# RAG function
def simple_rag(query, user_role="Recruiter"):
    # Embed query
    query_emb = embedder.encode([query])[0]

    # Filter indices dựa role
    allowed_indices = gatekeeper_filter(user_role)
    if not allowed_indices:
        return "No access to data."

    # Retrieve top 3 từ allowed docs
    allowed_embs = np.array([doc_embeddings[i] for i in allowed_indices]).astype('float32')
    allowed_index = faiss.IndexFlatL2(allowed_embs.shape[1])
    allowed_index.add(allowed_embs)
    distances, indices = allowed_index.search(np.array([query_emb]).astype('float32'), k=3)

    # Get contexts
    contexts = [documents[allowed_indices[i]] for i in indices[0] if i != -1]
    context_str = "\n".join(contexts)

    # Generate với GROQ
    prompt = f"Answer based on verified context only: {context_str}\nQuestion: {query}\nAnswer:"
    client = Groq(api_key=os.environ['GROQ_API_KEY'])
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",  # Hoặc "mixtral-8x7b-32768"
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,  # Tùy chỉnh
            max_tokens=512    # Giới hạn output
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"Error: {e}"

# Giao diện Streamlit
st.title("RAG Demo App")
st.write("Hỏi về kỹ năng hoặc dữ liệu liên quan. Chọn role để kiểm tra access.")

# Input từ user
user_role = st.selectbox("Chọn role:", ["Owner", "Recruiter", "Anonymous"])
query = st.text_input("Nhập câu hỏi (tiếng Anh hoặc tiếng Việt):")

if st.button("Trả lời"):
    if query:
        with st.spinner("Đang xử lý..."):
            answer = simple_rag(query, user_role)
        st.success("Kết quả:")
        st.write(answer)
    else:
        st.warning("Vui lòng nhập câu hỏi.")

# Phần test
# if __name__ == "__main__":
#     print("Owner:", simple_rag("What skills does A have?", "Owner"))
#     print("Recruiter:", simple_rag("What skills does A have?", "Recruiter"))
#     print("Anonymous:", simple_rag("What skills does A have?", "Anonymous"))
#     print("Owner:", simple_rag("Kỹ năng của A là gì?", "Owner"))
#     print("Recruiter:", simple_rag("Kỹ năng của A là gì?", "Recruiter"))
#     print("Anonymous:", simple_rag("Kỹ năng của A là gì?", "Anonymous"))