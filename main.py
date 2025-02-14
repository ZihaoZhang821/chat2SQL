import ollama
import sqlite3
import re
import customtkinter as ctk

# connect database
db_path = ""
db_connection = sqlite3.connect(db_path)
cursor = db_connection.cursor()

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# **📌 get information about table and field**
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]

db_schema = {}  # store information about table and field
for table in tables:
    cursor.execute(f"PRAGMA table_info({table});")
    columns = [row[1] for row in cursor.fetchall()]
    db_schema[table] = columns  # store in dictionary

# **📌 prompt**
db_structure_info = "You are a text to SQL generator and your main goal is to assist the user, as much as possible, by converting the input text into correct SQLite statements.\n\nThe following are the database table and field names:\n\n"
for table, columns in db_schema.items():
    db_structure_info += f"table `{table}` 's field': {', '.join(columns)}\n"

# **📌 SQL extract**
def extract_sql_from_text(text):
    sql_blocks = re.findall(r'```sql\s+(.*?)```', text, re.DOTALL)
    if sql_blocks:
        return sql_blocks[0]

    sql_pattern = r'\b(SELECT|INSERT|UPDATE|DELETE)\b[\s\S]+?;'
    sql_matches = re.findall(sql_pattern, text, re.IGNORECASE)
    if sql_matches:
        return sql_matches[0]

    return "No valid SQL detected"

# **📌 SQL execute**
def execute_sql_query(sql_query):
    if not sql_query.strip().upper().startswith("SELECT"):
        return "⚠️ Only SELECT queries are allowed."

    try:
        cursor.execute(sql_query)
        results = cursor.fetchall()
        if results:
            column_names = [desc[0] for desc in cursor.description]
            result_text = " | ".join(column_names) + "\n" + "-" * 60 + "\n"
            for row in results:
                result_text += " | ".join(str(item) for item in row) + "\n"
        else:
            result_text = "✅ Query executed successfully, but no data found."

        return result_text
    except Exception as e:
        return f"❌ SQL Error: {str(e)}"

# **📌 send query to db**
def send_query():
    global messages

    user_input = entry.get()
    if not user_input.strip():
        return

    # **📌 dbinfo**
    user_input_with_db_info = db_structure_info + "\ninput: " + user_input

    entry.delete(0, ctk.END)
    chat_display.insert(ctk.END, f"\n👤 You: {user_input}\n")
    chat_display.yview(ctk.END)

    messages.append({"role": "user", "content": user_input_with_db_info})

    response_text = ""
    stream = ollama.chat(
        model="deepseek-r1:7b",
        messages=messages,
        stream=True
    )

    chat_display.insert(ctk.END, "🤖 Ollama: ")
    for chunk in stream:
        chat_display.insert(ctk.END, chunk["message"]["content"])
        chat_display.update_idletasks()
        response_text += chunk["message"]["content"]

    chat_display.insert(ctk.END, "\n")
    chat_display.yview(ctk.END)

    messages.append({"role": "assistant", "content": response_text})

    extracted_sql = extract_sql_from_text(response_text)
    sql_display.configure(state=ctk.NORMAL)
    sql_display.delete(1.0, ctk.END)
    sql_display.insert(ctk.END, extracted_sql)
    sql_display.configure(state=ctk.DISABLED)

    if extracted_sql != "No valid SQL detected":
        query_result = execute_sql_query(extracted_sql)
    else:
        query_result = "No valid SQL found in AI response."

    result_display.configure(state=ctk.NORMAL)
    result_display.delete(1.0, ctk.END)
    result_display.insert(ctk.END, query_result)
    result_display.configure(state=ctk.DISABLED)

# **📌 main window**
root = ctk.CTk()
root.title("Ollama Chatbot with SQL Execution")
root.geometry("900x600")  #

messages = []

# **📌 frme*
main_frame = ctk.CTkFrame(root)
main_frame.pack(fill="both", expand=True, padx=10, pady=10)

# **📌 left(AI chatbox)**
chat_frame = ctk.CTkFrame(main_frame)
chat_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

chat_label = ctk.CTkLabel(chat_frame, text="AI Response", font=("Arial", 12, "bold"))
chat_label.pack(pady=5)

chat_display = ctk.CTkTextbox(chat_frame, wrap="word")
chat_display.pack(padx=10, pady=5, fill="both", expand=True)
chat_display.configure(font=("Arial", 12))

# **📌 middle（SQL chatbox）**
sql_frame = ctk.CTkFrame(main_frame)
sql_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

sql_label = ctk.CTkLabel(sql_frame, text="Extracted SQL Statement", font=("Arial", 12, "bold"))
sql_label.pack(pady=5)

sql_display = ctk.CTkTextbox(sql_frame, wrap="word", fg_color="#eef2ff")
sql_display.pack(padx=10, pady=5, fill="both", expand=True)
sql_display.configure(state=ctk.DISABLED, font=("Arial", 12))

# **📌 right（SQL chatbox）**
result_frame = ctk.CTkFrame(main_frame)
result_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

result_label = ctk.CTkLabel(result_frame, text="SQL Query Result", font=("Arial", 12, "bold"))
result_label.pack(pady=5)

result_display = ctk.CTkTextbox(result_frame, wrap="word", fg_color="#fff3cd")
result_display.pack(padx=10, pady=5, fill="both", expand=True)
result_display.configure(state=ctk.DISABLED, font=("Arial", 12))

# **📌User input area**
input_frame = ctk.CTkFrame(root)
input_frame.pack(side="bottom", fill="x", padx=10, pady=10)

entry = ctk.CTkEntry(input_frame, font=("Arial", 14))
entry.pack(side="left", padx=5, pady=5, expand=True, fill="x")

send_button = ctk.CTkButton(input_frame, text="Send", command=send_query, font=("Arial", 12), fg_color="#4CAF50", text_color="white")
send_button.pack(side="right", padx=5)

# **📌 adjust Grid **
main_frame.columnconfigure(0, weight=1)
main_frame.columnconfigure(1, weight=1)
main_frame.columnconfigure(2, weight=1)
main_frame.rowconfigure(0, weight=1)

root.mainloop()

db_connection.close()