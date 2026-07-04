import streamlit as st
from pathlib import Path #to get the absolute path of the student.db file

# In modern LangChain, create_sql_agent is imported from langchain_community.agent_toolkits instead of langchain.agents
from langchain_community.agent_toolkits import create_sql_agent#create_sql_agent is a LangChain function that creates an AI agent capable of querying SQL databases using natural language. It combines LLM with a SQL database so the agent can understand a user's question, generate the required SQL query, execute it on the database, and return the results in a human-readable format, eliminating the need to write SQL queries manually.

# In modern LangChain, SQLDatabase is imported from langchain_community.utilities instead of langchain.sql_database
from langchain_community.utilities import SQLDatabase

# The AgentType enum from langchain.agents.agent_types is deprecated. We pass the agent type as a string directly.

# In modern LangChain, StreamlitCallbackHandler is imported from langchain_community.callbacks.streamlit instead of langchain.callbacks
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler

# In modern LangChain, SQLDatabaseToolkit is imported from langchain_community.agent_toolkits instead of langchain.agents.agent_toolkits
from langchain_community.agent_toolkits import SQLDatabaseToolkit #SQLDatabaseToolkit is a LangChain class that provides a collection of SQL-related tools to an AI agent. It equips the agent with capabilities such as listing database tables, inspecting table schemas, executing SQL queries, and validating queries, allowing the agent to interact with a SQL database intelligently and answer users' natural language questions.

from sqlalchemy import create_engine#from sqlalchemy import create_engine is used to create a connection (engine) between your Python application and a database. The engine acts as the interface through which SQLAlchemy communicates with the database, allowing you to execute SQL queries, create tables, insert, update, delete, and retrieve data. It is typically the first step when working with databases using SQLAlchemy.

import sqlite3
from langchain_groq import ChatGroq

st.set_page_config(page_title="LangChain: Chat with SQL DB", page_icon="🦜")
st.title("🦜 LangChain: Chat with SQL DB")

#An Injection warning may be given here as: SQL agent can be vulnerable to prompt injection. Use a DB role with limited permissions. For example, if the database has multiple schemas, grant the agent access to only one schema. If the database has multiple tables, grant the agent access to only the tables it needs. If the database has multiple users, grant the agent access to only the users it needs.

LOCALDB="USE_LOCALDB"
MYSQL="USE_MYSQL"

radio_opt=["Use SQLite3 Database - Student.db","Connect to your MySQL Database"]

selected_opt=st.sidebar.radio(label="Choose the DB which you want to chat",options=radio_opt)

if radio_opt.index(selected_opt)==1:
    db_uri=MYSQL
    mysql_host=st.sidebar.text_input("Provide MySQL Host")
    mysql_user=st.sidebar.text_input("MYSQL User")
    mysql_password=st.sidebar.text_input("MYSQL password",type="password")
    mysql_db=st.sidebar.text_input("MySQL database")
else:
    db_uri=LOCALDB

api_key=st.sidebar.text_input(label="GROQ API Key",type="password")

if not db_uri:
    st.info("Please enter the database information and uri")

if not api_key:
    st.info("Please add the groq api key")

## LLM model
llm=ChatGroq(groq_api_key=api_key, model_name="llama-3.3-70b-versatile",streaming=True)

@st.cache_resource(ttl="2h")#till 2hrs it will be in the Cache so that we dont have to connect to DB each time. 
def configure_db(db_uri,mysql_host=None,mysql_user=None,mysql_password=None,mysql_db=None):
    if db_uri==LOCALDB:
        dbfilepath=(Path(__file__).parent/"student.db").absolute()#absolute file path
        print(dbfilepath)

        #The first line creates a small function (creator) that opens the SQLite database in read-only mode (mode=ro). This ensures the database can only be queried, preventing any changes such as inserting, updating, or deleting data.
        creator = lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro", uri=True)

        # The second line first creates a SQLAlchemy engine using create_engine(), but instead of creating its own connection, it uses the custom creator function defined above. This engine is then passed to SQLDatabase(), which wraps it into a LangChain-compatible database object. As a result, LangChain agents can safely execute SQL queries on the database while keeping it read-only.
        return SQLDatabase(create_engine("sqlite:///", creator=creator))
    elif db_uri==MYSQL:
        if not (mysql_host and mysql_user and mysql_password and mysql_db):
            st.error("Please provide all MySQL connection details.")
            st.stop()
        #connect to MySQL database. This engine is then passed to SQLDatabase(), which wraps it into a LangChain-compatible database object. As a result, LangChain agents can safely execute SQL queries on the database while keeping it read-only.
        return SQLDatabase(create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"))   
    
if db_uri==MYSQL:
    db=configure_db(db_uri,mysql_host,mysql_user,mysql_password,mysql_db)
else:
    db=configure_db(db_uri)

## toolkit
toolkit=SQLDatabaseToolkit(db=db,llm=llm)

print("\nAvailable SQL Tools:")
for tool in toolkit.get_tools():
    print(f"- {tool.name}")

# The AgentType enum is deprecated. We now pass the equivalent agent type string "zero-shot-react-description" directly.
agent=create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type="zero-shot-react-description"
)

if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

#This code displays the previous chat history stored in Streamlit's session state. It loops through every message in st.session_state.messages, and for each message, st.chat_message(msg["role"]) creates either a user or assistant chat bubble based on the "role", while .write(msg["content"]) displays the actual message text inside that bubble. This ensures that all earlier messages remain visible whenever the app reruns.
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

user_query=st.chat_input(placeholder="Ask anything from the database")

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)#write on screen.

    with st.chat_message("assistant"):
        streamlit_callback=StreamlitCallbackHandler(st.container())#for displaying the thoughts of agent.
        # The agent.run method is deprecated in modern LangChain in favor of agent.invoke. 
        # We extract the text output from the resulting dictionary.
        response=agent.invoke({"input": user_query},callbacks=[streamlit_callback])["output"]
        st.session_state.messages.append({"role":"assistant","content":response})
        st.write(response)
