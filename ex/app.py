# --- IMPORTS ---
import os
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import re
import psycopg2
from psycopg2 import pool
import time
from flask import Flask, request, jsonify, render_template, session
from datetime import timedelta
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
import chromadb
from typing import Dict, Any, List, Optional, Tuple # <--- FIX 1: Imported Tuple

# --- CONFIGURATION LOADING ---
# Load config once at startup and provide easy access to key values.
def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """Loads the configuration file and handles potential errors."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        print("✅ Config.json loaded successfully.")
        return config_data
    except FileNotFoundError:
        print(f"❌ FATAL: config.json not found at {config_path}")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ FATAL: Error decoding config.json: {e}")
        exit(1)

config = load_config()

# --- CENTRALIZED PERSONA & PROMPTS ---
# Define persona details and prompts centrally for easy modification.
PERSONA_CONFIG = config.get("persona", {})
PERSONA_NAME = PERSONA_CONFIG.get("name", "هوش‌کال")
CORE_GOAL = PERSONA_CONFIG.get("core_goal_persian", "هدف من کمک به شما برای بهبود مرکز تماستان است.")
TONE_OF_VOICE = ", ".join(PERSONA_CONFIG.get("tone_of_voice_persian", ["حرفه‌ای", "یاری‌رسان"]))

# Base system prompt to ensure consistent AI personality.
SYSTEM_PROMPT_BASE = f"""شما {PERSONA_NAME} هستید، یک دستیار هوشمند صوتی.
هدف اصلی شما: {CORE_GOAL}
لحن صدای شما باید: {TONE_OF_VOICE}.
"""

# --- SINGLETON FOR AI MODELS ---
# This class ensures large models are loaded only ONCE into memory.
class ModelSingleton:
    """Singleton class to load and hold AI models and tokenizer."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelSingleton, cls).__new__(cls)
            cls._instance.initialize_models()
        return cls._instance

    def initialize_models(self):
        """Loads all AI models and the tokenizer on first instantiation."""
        self.gpu_available = torch.cuda.is_available()
        self.device = "cuda" if self.gpu_available else "cpu"
        gpu_name = torch.cuda.get_device_name(0) if self.gpu_available else "N/A"
        print(f"✅ GPU available: {self.gpu_available}, Device: {self.device}, GPU Name: {gpu_name}")

        local_model_path = config.get("local_model_path", r"F:\call-center-framework\models\Meta-Llama-3-8B-Instruct")

        try:
            print(f"Loading Llama model from: {local_model_path}...")
            self.tokenizer = AutoTokenizer.from_pretrained(local_model_path)
            self.llama_model = AutoModelForCausalLM.from_pretrained(
                local_model_path,
                torch_dtype=torch.float16 if self.gpu_available else torch.float32,
                device_map="auto"
            )
            print("✅ Llama model and tokenizer loaded successfully.")
        except Exception as e:
            print(f"❌ FATAL: Error loading Llama model: {e}. Check path and files.")
            exit(1)

        try:
            print("Loading embedding model for RAG...")
            embedding_model_name = 'paraphrase-multilingual-MiniLM-L12-v2'
            self.embedding_model = SentenceTransformer(embedding_model_name)
            print("✅ Embedding model loaded successfully.")
        except Exception as e:
            print(f"❌ FATAL: Error loading embedding model: {e}. Make sure 'sentence-transformers' is installed.")
            exit(1)

    def generate_llama_response(self, prompt: str) -> str:
        """Generates a response using the loaded Llama model."""
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=2048).to(self.device)
            terminators = [
                self.tokenizer.eos_token_id,
                self.tokenizer.convert_tokens_to_ids("<|eot_id|>")
            ]
            outputs = self.llama_model.generate(
                inputs.input_ids, max_new_tokens=256, eos_token_id=terminators,
                do_sample=True, temperature=0.7, top_p=0.9, pad_token_id=self.tokenizer.eos_token_id
            )
            response_text = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            return response_text.strip()
        except Exception as e:
            print(f"❌ Error generating Llama response: {e}")
            return "متاسفانه در حال حاضر قادر به پاسخگویی نیستم. لطفاً کمی بعدتر امتحان کنید."

# Instantiate the singleton. This will load the models upon starting the app.
models = ModelSingleton()


# --- DATABASE MANAGEMENT (with Connection Pooling) ---
db_pool = None
def initialize_database_pool():
    """Initializes the PostgreSQL connection pool."""
    global db_pool
    try:
        db_config = config.get("database", {})
        db_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1, maxconn=10, # Adjust maxconn based on expected traffic
            host=db_config.get("host"), port=db_config.get("port"),
            dbname=db_config.get("dbname"), user=db_config.get("user"),
            password=db_config.get("password")
        )
        print("✅ Database connection pool created successfully.")
    except psycopg2.OperationalError as e:
        print(f"❌ FATAL: Could not create database connection pool. Error: {e}")
        exit(1)

def initialize_db_schema():
    """Creates the 'conversations' table if it doesn't exist."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY, customer_name VARCHAR(255), phone_number VARCHAR(20),
                    company_name VARCHAR(255), conversation_duration_seconds INTEGER,
                    purchase_confirmed BOOLEAN, model_score INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            print("✅ 'conversations' table verified successfully.")
    except Exception as e:
        print(f"❌ Error during schema initialization: {e}")
    finally:
        db_pool.putconn(conn)

def save_conversation_data(conversation_data: Dict[str, Any]):
    """Saves conversation data using a connection from the pool."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            duration = int(time.time() - conversation_data["start_time"]) if conversation_data.get("start_time") else 0
            insert_query = """
            INSERT INTO conversations (customer_name, phone_number, company_name,
                                         conversation_duration_seconds, purchase_confirmed, model_score)
            VALUES (%s, %s, %s, %s, %s, %s);
            """
            cur.execute(insert_query, (
                conversation_data.get("customer_name"), conversation_data.get("phone_number"),
                conversation_data.get("business_name"), duration,
                conversation_data.get("demo_request_accepted", False), conversation_data.get("model_score", 0)
            ))
            conn.commit()
            print("✅ Conversation data saved to database.")
    except Exception as e:
        print(f"❌ Error saving conversation data: {e}")
        conn.rollback()
    finally:
        db_pool.putconn(conn)


# --- VECTOR DATABASE (ChromaDB) ---
chroma_client = None
faq_collection = None
def initialize_vector_db():
    """Initializes ChromaDB and populates it with FAQ data."""
    global chroma_client, faq_collection
    try:
        chroma_client = chromadb.PersistentClient(path="./chroma_db_data")
        faq_collection_name = "faq_knowledge_base"
        faq_collection = chroma_client.get_or_create_collection(name=faq_collection_name)
        print(f"✅ ChromaDB collection '{faq_collection_name}' loaded. Contains {faq_collection.count()} items.")

        if faq_collection.count() == 0:
            print("Populating ChromaDB with FAQ data...")
            documents, metadatas, ids = [], [], []
            for i, item in enumerate(config.get("knowledge_base", {}).get("faq", [])):
                for j, question in enumerate(item.get("example_questions_persian", [])):
                    documents.append(question)
                    metadatas.append({
                        "approved_answer": item["approved_answer_persian"],
                        "category": item["question_category"]
                    })
                    ids.append(f"faq_{i}_{j}")

            if documents:
                embeddings = models.embedding_model.encode(documents).tolist()
                faq_collection.add(embeddings=embeddings, documents=documents, metadatas=metadatas, ids=ids)
                print(f"✅ Added {len(documents)} FAQ entries to ChromaDB.")
    except Exception as e:
        print(f"❌ FATAL: Error initializing ChromaDB: {e}")
        exit(1)

def retrieve_context_from_faq(user_question: str, n_results: int = 1) -> List[str]:
    """Retrieves relevant answers from ChromaDB."""
    try:
        query_embedding = models.embedding_model.encode(user_question).tolist()
        results = faq_collection.query(
            query_embeddings=[query_embedding], n_results=n_results, include=['metadatas']
        )
        if results and results['metadatas'] and results['metadatas'][0]:
            return [meta['approved_answer'] for meta in results['metadatas'][0] if 'approved_answer' in meta]
        return []
    except Exception as e:
        print(f"❌ Error retrieving from ChromaDB: {e}")
        return []


# --- UTILITY FUNCTIONS ---
def check_for_rules(user_input: str) -> Optional[str]:
    """Checks if input triggers predefined deflection rules."""
    rules = config.get("rules_and_boundaries", {}).get("rules", [])
    for rule in rules:
        if any(keyword.lower() in user_input.lower() for keyword in rule.get("triggering_keywords_persian", [])):
            return rule.get("deflection_script_persian", "متاسفانه نمی‌توانم در این مورد صحبت کنم.")
    return None

def generate_llm_chat_response(messages: List[Dict[str, str]]) -> str:
    """Applies chat template and generates response."""
    full_prompt = models.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return models.generate_llama_response(full_prompt)

# --- SALES WORKFLOW LOGIC ---
# The core logic for handling the sales conversation is kept here.
def handle_sales_workflow(user_input: str, conversation_state: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]: # <--- FIX 2: Corrected return type
    """Manages the sales workflow, processing user input and advancing the conversation."""
    workflow_steps = config.get("sales_workflow", {}).get("questionnaire", [])
    current_stage = conversation_state["stage"]

    # --- Handling Score Input ---
    if conversation_state.get("_awaiting_score"):
        try:
            score = int(user_input.strip())
            if 1 <= score <= 5:
                conversation_state["data"]["model_score"] = score
                save_conversation_data(conversation_state["data"])
                # Reset for a new conversation
                return "از امتیاز شما متشکرم! اگر سوال دیگری دارید، در خدمتم.", get_initial_session_state()
            else:
                return "لطفاً یک عدد بین ۱ تا ۵ وارد کنید.", conversation_state
        except ValueError:
            return "لطفاً یک عدد معتبر برای امتیاز وارد کنید.", conversation_state

    # --- Starting the Workflow ---
    if current_stage == 0:
        initial_keywords = ["سلام", "وقت بخیر", "کمک", "میخوام", "صحبت", "معرفی", "شروع", "بله", "اوکی"]
        if any(keyword in user_input.lower() for keyword in initial_keywords):
            conversation_state["stage"] = 1
            conversation_state["data"] = {}
            conversation_state["start_time"] = time.time()
            first_question = workflow_steps[0]["question_to_ask_persian"]

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_BASE + f" وظیفه شما شروع یک مکالمه فروش است. سوال اول شما این است: {first_question}"},
                {"role": "user", "content": user_input}
            ]
            response = generate_llm_chat_response(messages)
            return response or first_question, conversation_state

    # --- Processing Workflow Steps ---
    if 0 < current_stage <= len(workflow_steps):
        step_config = workflow_steps[current_stage - 1]
        info_to_capture = step_config.get("information_to_capture")
        data_captured = False

        # Simplified data extraction logic (can be expanded with more regex)
        if "customer_name" in info_to_capture and "business_name" in info_to_capture:
            # This regex is an example; it may need to be more robust
            match = re.search(r"([\u0600-\u06FF\s]+)\s*(?:هستم از شرکت|از)\s*([\u0600-\u06FF\d\s]+)", user_input, re.I)
            if match:
                conversation_state["data"]["customer_name"] = match.group(1).strip()
                conversation_state["data"]["business_name"] = match.group(2).strip()
                data_captured = True

        elif "demo_request_accepted" in info_to_capture:
            positive_keywords = ["بله", "میخوام", "می‌خواهم", "تمایل دارم", "حتما", "لطفا"]
            is_accepted = any(keyword in user_input.lower() for keyword in positive_keywords)
            conversation_state["data"]["demo_request_accepted"] = is_accepted
            data_captured = True

            if is_accepted:
                conversation_state["_awaiting_score"] = True
                prompt_task = "کاربر درخواست دمو را پذیرفته است. یک پاسخ حرفه‌ای برای تایید درخواست ارائه دهید و سپس برای ارزیابی کیفیت مکالمه، از او بخواهید از ۱ تا ۵ امتیاز دهد."
                messages = [{"role": "system", "content": SYSTEM_PROMPT_BASE + prompt_task}, {"role": "user", "content": user_input}]
                response = generate_llm_chat_response(messages)
                return response or "بسیار عالی! همکاران ما برای هماهنگی جلسه دمو با شما تماس خواهند گرفت. به کیفیت این مکالمه از ۱ تا ۵ چه امتیازی می‌دهید؟", conversation_state
            else:
                prompt_task = "کاربر درخواست دمو را رد کرده است. یک پیام مودبانه برای پایان گفتگو ارائه دهید."
                messages = [{"role": "system", "content": SYSTEM_PROMPT_BASE + prompt_task}, {"role": "user", "content": user_input}]
                response = generate_llm_chat_response(messages)
                save_conversation_data(conversation_state["data"])
                return response or "متوجه شدم. اگر در آینده سوالی داشتید، خوشحال می‌شوم کمک کنم.", get_initial_session_state()

        # Add other 'elif' blocks for other info_to_capture types here...

        # --- Advancing to the Next Stage ---
        if data_captured:
            conversation_state["stage"] += 1
            if conversation_state["stage"] > len(workflow_steps):
                # Workflow finished, but not via demo request (should be rare)
                save_conversation_data(conversation_state["data"])
                return "ممنون از اطلاعات شما. آیا کار دیگری هست که بتوانم برایتان انجام دهم؟", get_initial_session_state()

            next_question = workflow_steps[conversation_state["stage"] - 1]["question_to_ask_persian"]
            # Format question with already captured data
            for key, value in conversation_state["data"].items():
                if f"[{key}]" in next_question:
                    next_question = next_question.replace(f"[{key}]", str(value))
            
            prompt_task = f"شما با موفقیت اطلاعات قبلی را دریافت کردید. حالا با یک انتقال نرم، سوال بعدی را بپرسید: {next_question}"
            messages = [{"role": "system", "content": SYSTEM_PROMPT_BASE + prompt_task}, {"role": "user", "content": user_input}]
            response = generate_llm_chat_response(messages)
            return response or next_question, conversation_state
        else:
            # Data not captured, re-ask the question
            current_question = step_config["question_to_ask_persian"]
            prompt_task = f"کاربر پاسخ واضحی به سوال نداده است. لطفاً سوال را به شکل دیگری تکرار کنید. سوال اصلی این بود: {current_question}"
            messages = [{"role": "system", "content": SYSTEM_PROMPT_BASE + prompt_task}, {"role": "user", "content": user_input}]
            response = generate_llm_chat_response(messages)
            return response or f"متوجه نشدم. {current_question}", conversation_state

    # Fallback if something goes wrong with stage logic
    return "متاسفانه در روند گفتگو مشکلی پیش آمده است. لطفاً دوباره تلاش کنید.", conversation_state


# --- FLASK APPLICATION ---
app = Flask(__name__)
CORS(app)
app.secret_key = os.urandom(24) # For production, use an environment variable
app.permanent_session_lifetime = timedelta(minutes=30)

def get_initial_session_state() -> Dict[str, Any]:
    """Returns the default dictionary for a new user session."""
    return {
        "stage": 0, "data": {}, "start_time": None, "_awaiting_score": False,
        "consecutive_unanswered_prompts": 0, "last_prompt_stage": 0
    }

@app.route('/')
def index():
    """Renders the main chat interface."""
    session.permanent = True
    if 'conversation_state' not in session:
        session['conversation_state'] = get_initial_session_state()
    initial_greeting = PERSONA_CONFIG.get("introduction_script", "سلام! چطور می‌توانم کمکتان کنم؟")
    gpu_status = f"✅ GPU فعال: {torch.cuda.get_device_name(0)}" if models.gpu_available else "❌ GPU در دسترس نیست (CPU)"
    return render_template('index.html', initial_greeting=initial_greeting, gpu_status=gpu_status)

@app.route('/chat', methods=['POST'])
def chat():
    """Handles all incoming chat messages and orchestrates the response."""
    user_input = request.json.get('message', '').strip()
    conversation_state = session.get('conversation_state', get_initial_session_state())
    response = "متاسفانه خطایی رخ داده است." # Default error message

    try:
        # Priority 1: Check for hard-coded rules
        if (rule_response := check_for_rules(user_input)):
            response = rule_response

        # Priority 2: Handle ongoing sales workflow or score collection
        elif conversation_state["stage"] > 0 or conversation_state.get("_awaiting_score"):
            response, conversation_state = handle_sales_workflow(user_input, conversation_state)

        # Priority 3: General Q&A and workflow initiation
        else:
            # Try RAG first
            relevant_answers = retrieve_context_from_faq(user_input, n_results=1)
            if relevant_answers:
                context = "\n\n**اطلاعات مرتبط از پایگاه دانش:**\n" + "\n".join(relevant_answers)
                messages = [{"role": "system", "content": SYSTEM_PROMPT_BASE + context}, {"role": "user", "content": user_input}]
                response = generate_llm_chat_response(messages)
            else:
                # If no FAQ, check if user wants to start workflow
                initial_keywords = ["سلام", "وقت بخیر", "کمک", "صحبت", "معرفی", "شروع", "بله", "اوکی"]
                if any(keyword in user_input.lower() for keyword in initial_keywords):
                    response, conversation_state = handle_sales_workflow(user_input, conversation_state)
                else:
                    # Fallback to general LLM chat without RAG context
                    messages = [{"role": "system", "content": SYSTEM_PROMPT_BASE}, {"role": "user", "content": user_input}]
                    response = generate_llm_chat_response(messages)

    except Exception as e:
        print(f"❌ CRITICAL ERROR in /chat endpoint: {e}")
        conversation_state = get_initial_session_state() # Reset state on critical error
        response = "یک خطای داخلی رخ داده است. لطفاً صفحه را مجدداً بارگیری کنید."

    session['conversation_state'] = conversation_state
    print(f"User: {user_input}\nAssistant: {response}\nState: {conversation_state}\n" + "-"*50)
    return jsonify({'response': response})

# --- MAIN EXECUTION BLOCK ---
if __name__ == '__main__':
    # Initialize all components on startup
    initialize_database_pool()
    initialize_db_schema()
    initialize_vector_db()
    # The 'models' singleton is automatically initialized when the script is loaded.

    # For development ONLY. Use a production-grade WSGI server for deployment.
    # Example: gunicorn --workers 4 --threads 2 --timeout 120 --bind 0.0.0.0:5000 app:app
    app.run(debug=True, host='0.0.0.0', port=5000)