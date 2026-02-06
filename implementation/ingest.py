import os
import glob
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from pathlib import Path

def load_multiple_md_files(base_path: str):
    """
    Wczytujemy kilka plików .md z danymi

    Returns:
        List[Document]: Lista dokumentów z metadanymi
    """
    documents = []
    folders = [f for f in glob.glob(f"{base_path}/*") if os.path.isdir(f)]

    for folder in folders:
        doc_type = os.path.basename(folder)

        loader = DirectoryLoader(
            folder,
            glob = "**/*.md",
            loader_cls = TextLoader,
            loader_kwargs = {"encoding": "utf-8"},
            recursive = True
        )

        folder_docs = loader.load()

        for doc in folder_docs:
            file_path = doc.metadata.get('source', '')
            file_name = Path(file_path).stem

            doc.metadata.update({
                "doc_type": doc_type,
                "format": "markdown",
                "file_name": file_name,
                "file_stem": file_name.lower().replace(' ', '_'),
                "category": doc_type,
                "entity_name": file_name
            })

        documents.extend(folder_docs)
        print(f"{doc_type}: {len(folder_docs)} plików .md")

    print(f"\nRazem: {len(documents)} dokumentów")
    return documents

docs = load_multiple_md_files("knowledge-base")

if docs:
    print(f"\nPrzykład metadanych:")
    print(f"  Treść: {docs[0].page_content[:100]}...")
    print(f"  Metadane: {docs[0].metadata}")

