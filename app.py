from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from langchain_openai import AzureOpenAIEmbeddings
import requests
from typing import Optional
import json
import ast
from src.build_graph_db import *
from src.hs_code_classifier import *
from src.hs_code_scrapers import *



class Item(BaseModel):
    cargo_desc: str


app = FastAPI()
templates = Jinja2Templates(directory="templates")


load_dotenv()

# Retrieve environment variables
api_version = os.getenv("AZURE_API_VERSION")
azure_endpoint = os.getenv("AZURE_ENDPOINT")
azure_embedding_deployment = os.getenv("AZURE_EMBEDDING_DEPLOYMENT")
azure_gpt_deployment = os.getenv("AZURE_GPT_DEPLOYMENT")
api_key = os.getenv("AZURE_API_KEY")
neo4j_url = os.getenv("NEO4J_URL")
neo4j_username = os.getenv("NEO4J_USERNAME")
neo4j_password = os.getenv("NEO4J_PASSWORD")
ENDPOINT = f"{azure_endpoint}openai/deployments/{azure_gpt_deployment}/chat/completions?api-version={api_version}"


# Initialize Azure OpenAI Embeddings
embed = AzureOpenAIEmbeddings(
    api_version=api_version,
    azure_endpoint=azure_endpoint,
    azure_deployment=azure_embedding_deployment,
    api_key=api_key
)

# Initialize Neo4j Vector
graph = Neo4jVector.from_existing_graph(
    embedding=embed,
    url=neo4j_url,
    username=neo4j_username,
    password=neo4j_password,
    index_name="HS4",
    node_label="HS4",
    text_node_properties=["nameC", "nameE"],
    embedding_node_property="embedding",
)


@app.get("/", response_class=HTMLResponse)
def form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

@app.post("/api")
def create_task(item: Item):
    top_hs4_codes = graph.similarity_search(item.cargo_desc, k=10)
    result = []
    for hs4 in top_hs4_codes:
        input_str = hs4.page_content.strip()
        pairs = input_str.split('\n')
        result_dict = {}
        for pair in pairs:
            key, value = pair.split(': ', 1)
            result_dict[key] = value
        result_dict['hs4'] = hs4.metadata['hs4']
        result.append(result_dict)

    max_retries = 5
    for attempt in range(max_retries):
        try:
            classification = classify_commodity(item.cargo_desc, str(result), api_key, ENDPOINT)
            classification = ast.literal_eval(classification)
            break 
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(1) 
            else:
                print("All attempts failed.")
                classification = None  

    hs4_codes = [item[0] for item in classification]
    rationales = [item[1] for item in classification]

    print(hs4_codes)
    print(rationales)
    return {"hs4_codes": hs4_codes, "rationales": rationales}
    





