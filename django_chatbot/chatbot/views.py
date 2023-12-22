from django.shortcuts import render
from django.http import JsonResponse
from decouple import config
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.agents import Tool
from sqlalchemy.engine import make_url
from llama_index.indices.vector_store import VectorStoreIndex
from llama_index.vector_stores import PGVectorStore
from llama_index.llama_pack import download_llama_pack
from llama_index.postprocessor import MetadataReplacementPostProcessor
import psycopg2
import os


# get api key from .env file
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY = config('OPENAI_API_KEY')


#initialize vectorstore config
connection_string = config('PGVECTOR_CONNECTION_STRING')
db_name = config('PGVECTOR_DATABASE')
conn = psycopg2.connect(connection_string)
conn.autocommit = True
url = make_url(connection_string)

vector_store = PGVectorStore.from_params(
    database=db_name,
    host=url.host,
    password=url.password,
    port=url.port,
    user=url.username,
    table_name="DeloitteFutureOfAI",
    embed_dim=1536,  # openai embedding dimension
)
#create index
index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
query_engine = index.as_query_engine()

#for sentence window retriever
# index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
# query_engine = index.as_query_engine(
#     similarity_top_k=3,
#     # the target key defaults to `window` to match the node_parser's default
#     node_postprocessors=[
#         MetadataReplacementPostProcessor(target_metadata_key="test")
#     ],
# )

#create langchain tool
tools = [
    Tool(
        name="Deloitte Future Of AI Report",
        func=lambda q: str(index.as_query_engine().query(q)),
        description="Useful only when there are questions about Deloitte Future Of AI report. This is not useful for general knowledge",
        return_direct=True,
    ),
]

memory = ConversationBufferWindowMemory(memory_key="chat_history", k=6)

llm = ChatOpenAI(temperature=0, api_key=OPENAI_API_KEY, model='gpt-4')
agent_executor = initialize_agent(
    tools=tools, 
    llm=llm, 
    #agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
    agent="conversational-react-description", memory=memory,
    verbose=True,
    handle_parsing_errors=False
)

#Create RAG Pipeline
def ask_openai_rag(message):
    answer = agent_executor.run(input=message)
    return answer


def chatbot(request):
    if request.method == 'POST':
        message = request.POST.get('message')
        response = ask_openai_rag(message)
        return JsonResponse({'message': message, 'response': response})
    return render(request,'chatbot.html')