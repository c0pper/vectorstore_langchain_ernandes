from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
import os
from langchain.document_loaders import PDFMinerPDFasHTMLLoader
import logging
from bs4 import BeautifulSoup
import re
from langchain.llms import OpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain.prompts.prompt import PromptTemplate


from dotenv import load_dotenv

PDF_NAME = "silvanus"
PDF_LANG = "en"
PERSIST_DIRECTORY = f"{PDF_NAME}_db"

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

logging.basicConfig(filename=f'{PDF_NAME}.log', filemode='a', format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)


# BASIC APPROACH
from langchain.document_loaders import PyPDFLoader

def load_pdf_basic(pdf_name):
    # An advantage of this approach is that documents can be retrieved with page numbers.

    loader = PyPDFLoader(f"{pdf_name}.pdf")
    docs = loader.load_and_split()

    return docs



# HTML APPROACH
def load_pdf_in_html(pdf_name):
    loader = PDFMinerPDFasHTMLLoader(f"{pdf_name}.pdf")
    data = loader.load()[0]
    soup = BeautifulSoup(data.page_content,'html.parser')
    content = soup.find_all('div')
    
    return {"content": content, "loader_data": data}


def split_content_semantically(loaded_pdf):
    cur_fs = None
    cur_text = ''
    snippets = []   # first collect all snippets that have the same font size
    for c in loaded_pdf["content"]:
        sp = c.find('span')
        if not sp:
            continue
        st = sp.get('style')
        if not st:
            continue
        fs = re.findall('font-size:(\d+)px', st)
        if not fs:
            continue
        fs = int(fs[0])
        if not cur_fs:
            cur_fs = fs
        if fs == cur_fs:
            cur_text += c.text
        else:
            snippets.append((cur_text,cur_fs))
            cur_fs = fs
            cur_text = c.text
    snippets.append((cur_text,cur_fs))
    # Note: The above logic is very straightforward. One can also add more strategies such as removing duplicate snippets (as
    # headers/footers in a PDF appear on multiple pages so if we find duplicates it's safe to assume that it is redundant info)

    from langchain.docstore.document import Document
    cur_idx = -1
    semantic_snippets = []
    # Assumption: headings have higher font size than their respective content
    for s in snippets:
        # if current snippet's font size > previous section's heading => it is a new heading
        if not semantic_snippets or s[1] > semantic_snippets[cur_idx].metadata['heading_font']:
            metadata={'heading':s[0], 'content_font': 0, 'heading_font': s[1]}
            metadata.update(loaded_pdf["loader_data"].metadata)
            semantic_snippets.append(Document(page_content='',metadata=metadata))
            cur_idx += 1
            continue

        # if current snippet's font size <= previous section's content => content belongs to the same section (one can also create
        # a tree like structure for sub sections if needed but that may require some more thinking and may be data specific)
        if not semantic_snippets[cur_idx].metadata['content_font'] or s[1] <= semantic_snippets[cur_idx].metadata['content_font']:
            semantic_snippets[cur_idx].page_content += s[0]
            semantic_snippets[cur_idx].metadata['content_font'] = max(s[1], semantic_snippets[cur_idx].metadata['content_font'])
            continue

        # if current snippet's font size > previous section's content but less than previous section's heading than also make a new
        # section (e.g. title of a PDF will have the highest font size but we don't want it to subsume all sections)
        metadata={'heading':s[0], 'content_font': 0, 'heading_font': s[1]}
        metadata.update(loaded_pdf["loader_data"].metadata)
        semantic_snippets.append(Document(page_content='',metadata=metadata))
        cur_idx += 1

    for s in semantic_snippets:
        logging.info(f"{s.metadata}\n--{s.page_content}\n\n\n\n\n")
    
    return semantic_snippets


def create_vectorstore(docs=None):
    if PDF_LANG == "it":
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/distiluse-base-multilingual-cased-v2")
        print("Using italian embeddings")
    else:
        embeddings = HuggingFaceEmbeddings()
        print("Using english embeddings")


    #  If embeddings database already exists > read it, else > create it
    if os.path.exists(PERSIST_DIRECTORY) and os.path.isdir(PERSIST_DIRECTORY):
        print("Directory 'db' exists. Using existing vectordb")
        db = Chroma(persist_directory=PERSIST_DIRECTORY, embedding_function=embeddings)

    else:
        # pass
        if docs == None:
            raise ValueError("No docs found")
        else:
            db = Chroma.from_documents(docs, embeddings, persist_directory=PERSIST_DIRECTORY)
            print("Directory 'db' does not exist. Creating new vectordb")
            db.persist()

    return db






if __name__ == "__main__":
    if not os.path.exists(PERSIST_DIRECTORY):
        # HTML APPROACH
        # loaded_pdf = load_pdf_in_html(PDF_NAME)
        # split_content = split_content_semantically(loaded_pdf=loaded_pdf)

        # BASIC APPROACH
        split_content = load_pdf_basic(PDF_NAME)
        vs = create_vectorstore(docs=split_content)
    else:
        vs = create_vectorstore()

    # memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    llm = OpenAI(temperature=0)
    memory = ConversationSummaryMemory(llm=llm, return_messages=True, memory_key="chat_history")
    qa = ConversationalRetrievalChain.from_llm(OpenAI(temperature=0), vs.as_retriever(), memory=memory, verbose=True)

    while True:
        q = input()

        results = vs.similarity_search_with_score(q, k=6)
        formatted = [f"{r[0].metadata}\nScore: {r[1]}\n--\n{r[0].page_content}\n\n\n\n\n" for r in results]
        [logging.info(x) for x in formatted]
        [print(x) for x in formatted]

        
        result = qa({"question": q})

        logging.info(q)
        logging.info(f"History:\n{memory.load_memory_variables({})}\n\n")
        logging.info(result)
        print(q)
        print(f"History:\n{memory.load_memory_variables({})}\n\n")
        print(result)




