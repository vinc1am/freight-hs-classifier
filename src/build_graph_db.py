from langchain_community.graphs import Neo4jGraph
from langchain_openai import AzureOpenAIEmbeddings
import json
import time
import os
import requests
import uuid
from dotenv import load_dotenv
from langchain_community.vectorstores.neo4j_vector import Neo4jVector


def restore_graph(graph: Neo4jGraph) -> None:
    graph.query(
        """
        MATCH (n)
        DETACH DELETE n
        """
    )
    indexes = graph.query(
        """
        SHOW INDEX
        """
    )
    for idx in indexes:
        graph.query(
            f"""
            DROP INDEX `{idx["name"]}`
            """
        )
    return None

def add_hs_node(
        label: str, 
        properties: dict, 
        node_type: str,
        graph: Neo4jGraph,
    ) -> str: 
    node_id = str(uuid.uuid4())
    properties.setdefault("node_id", node_id)
    prop = ", ".join(
        f"{k}: {json.dumps(str(v))}" for k, v in properties.items()
    )
    graph.query(
        f"""
        MERGE (n:{label} {{{prop}}})
        """
    )
    node_type = node_type.upper() 
    if node_type in ["HS2", "HS4"]:
        graph.query(
            f"""
            MATCH (n:{label} {{node_id: '{node_id}'}})
            SET n:{label}_{node_type}, n:{node_type}
            """
        )
    elif node_type == "KB":
        graph.query(
            f"""
            MATCH (n:{label} {{node_id: '{node_id}'}})
            SET n:{label}_KB, n:KB
            """
        )
    else:
        raise ValueError("node_type must be one of 'HS2', 'HS4', or 'KB'")
    return node_id


def add_hs_relationship(
    relationship: str, pid: str, cid: str,
    graph: Neo4jGraph,
) -> None:
    graph.query(
        f"""
        MATCH (p {{node_id: '{pid}'}})
        MATCH (c {{node_id: '{cid}'}})
        MERGE (p)-[:{relationship}]->(c)
        """
    )
    return None

def add_hs_embedding(
    node_id: str, 
    context: str, 
    embedding_node_property: str, 
    embed: AzureOpenAIEmbeddings,
    graph: Neo4jGraph
) -> None:
    embed_vector = embed.embed_query(context)
    graph.query(
        f"""
        MATCH (n)
        WHERE n.node_id = '{node_id}'
        SET n.{embedding_node_property} = '{embed_vector}'
        """
    )
    return None

def create_hs_graph(hs_data, graph, embed, verbose=False):
    kb_name = "HS_CODE"
    kb_node_id = add_hs_node("KB", {"kb_name": kb_name}, "KB", graph=graph)
    for parent in hs_data:
        if verbose:
            print(parent['nameE'])
            print('=='*50)
        combined_name = f"{parent['nameE']} {parent['nameC']}"
        parent_node_id = add_hs_node("HS", {"hs2": parent['hs2'], "nameE": parent['nameE'], "nameC": parent['nameC']}, "HS2", graph=graph)
        add_hs_embedding(parent_node_id, combined_name, 'embedding_name', embed=embed, graph=graph)
        add_hs_relationship("BELONGS_TO", parent_node_id, kb_node_id, graph=graph)
        for child in parent['child']:
            combined_child_name = f"{child['nameE']} {child['nameC']}"
            child_node_id = add_hs_node("HS", {"hs4": child['hs4'], "nameE": child['nameE'], "nameC": child['nameC']}, "HS4", graph=graph)
            add_hs_embedding(child_node_id, combined_child_name, 'embedding_name', embed=embed, graph=graph)
            add_hs_relationship("CONTAINS", parent_node_id, child_node_id, graph=graph)
            
            if verbose:
                print(child)
                
        if verbose:
            print('')

def get_or_create_vector_index(
    model: AzureOpenAIEmbeddings,
    label: str, 
    embed_properties: list[str] = ["nameC", "nameE", "hs4"], 
    embedding_node_property: str = "embedding", 
    retrieve_properties: str = "hs4", 
    top_k_primary_kb: int = 10,
):

    retrieval_query = (
        f"RETURN node.{retrieve_properties} as text, "
        "node {.*, `"
        + embedding_node_property
        + "`: Null, id: Null} AS metadata, score "
        f"ORDER BY score DESC LIMIT {top_k_primary_kb} "
    )

    vector_index = Neo4jVector.from_existing_graph(
        embedding=model,
        url=os.getenv("NEO4J_URL"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        index_name=label,
        node_label=label,
        text_node_properties=embed_properties, 
        embedding_node_property=embedding_node_property,
        retrieval_query=retrieval_query,
    )

    return vector_index



if __name__ == "__main__":
    
    # Load environment variables from .env file
    load_dotenv()

    # Initial Neo4j 
    neo4j_url = os.getenv("NEO4J_URL")
    neo4j_username = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    graph = Neo4jGraph(
        url=neo4j_url,
        username=neo4j_username,
        password=neo4j_password,
    )
    
    # Initialize Embedding model
    api_version = os.getenv("AZURE_API_VERSION")
    azure_endpoint = os.getenv("AZURE_ENDPOINT")
    azure_embedding_deployment = os.getenv("AZURE_EMBEDDING_DEPLOYMENT")
    api_key = os.getenv("AZURE_API_KEY")
    embed = AzureOpenAIEmbeddings(
        api_version=api_version,
        azure_endpoint=azure_endpoint,
        azure_deployment=azure_embedding_deployment,
        api_key=api_key
    )

    restore_graph(graph=graph)
    print("[1/4] Restored Database")

    # hs4_data = fetch_hs4_codes()
    with open('../data/hs4_data.json', 'r') as file:
        hs4_data = json.load(file)
    print("[2/4] Fetch HS4 Code from C&S")
    
    create_hs_graph(hs4_data, graph=graph, embed=embed, verbose=True)
    print("[3/4] HS Graph Creation Completed")
    
    vector_index = get_or_create_vector_index(embed, "HS4")
    print("[4/4] Vector Index Completed")