import os
import google.generativeai as genai
from github import Github

def main():
    # 1. Configuration
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found.")
        return

    github_token = os.environ.get("GITHUB_TOKEN")
    repo_name = os.environ.get("REPO_NAME")
    issue_number = int(os.environ.get("ISSUE_NUMBER"))
    issue_body = os.environ.get("ISSUE_BODY")

    genai.configure(api_key=api_key)
    
    # Dynamic Model Selection
    print("Listing available models...")
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
                print(f"Found supported model: {m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")

    # Priority list of models to use
    priority_models = [
        'models/gemini-3-pro-preview',
        'models/gemini-2.0-pro-exp',
        'models/gemini-2.5-pro',
        'models/gemini-2.0-flash',
        'models/gemini-1.5-pro-latest',
        'models/gemini-1.5-pro',
        'models/gemini-1.5-flash',
        'models/gemini-pro'
    ]

    selected_model_name = None
    for priority in priority_models:
        if priority in available_models:
            selected_model_name = priority
            break
    
    # Fallback if exact match not found (or list failed), try the user's preference blindly or a safe default
    if not selected_model_name:
        print("Could not find a preferred model in the list. Attempting 'gemini-pro' as fallback.")
        selected_model_name = 'gemini-pro'

    print(f"Selected model: {selected_model_name}")
    model = genai.GenerativeModel(selected_model_name)

    # 2. Read current files
    # In a real scenario, we might want to list files or be smarter, 
    # but for this portfolio, we know the files.
    files_to_read = ["index.html", "style.css"]
    file_contents = {}
    
    for filename in files_to_read:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                file_contents[filename] = f.read()
        else:
            file_contents[filename] = "(File does not exist yet)"

    # 3. Construct Prompt
    prompt = f"""
    You are an expert web developer agent. 
    Your task is to modify the following website code based on the user's request.
    
    USER REQUEST:
    {issue_body}
    
    CURRENT FILE CONTENT:
    
    --- index.html ---
    {file_contents.get('index.html', '')}
    
    --- style.css ---
    {file_contents.get('style.css', '')}
    
    INSTRUCTIONS:
    1. Return the FULL content of the modified files. 
    2. If a file is not modified, do not return it.
    3. Use the following format strictly:
    
    FILE: index.html
    ```html
    ... full content of index.html ...
    ```
    
    FILE: style.css
    ```css
    ... full content of style.css ...
    ```
    
    Do not add any other conversational text. Just the file blocks.
    """

    # 4. Call AI
    print("Sending request to Gemini...")
    response = model.generate_content(prompt)
    response_text = response.text
    print("Received response from Gemini.")

    # 5. Parse and Apply Changes
    current_file = None
    code_block_active = False
    buffer = []
    
    lines = response_text.split('\n')
    for line in lines:
        if line.startswith("FILE: "):
            current_file = line.split("FILE: ")[1].strip()
            buffer = []
            code_block_active = False # Reset
        elif line.strip().startswith("```") and current_file:
            if code_block_active:
                # End of block, write file
                code_block_active = False
                new_content = "\n".join(buffer)
                print(f"Updating {current_file}...")
                with open(current_file, "w", encoding="utf-8") as f:
                    f.write(new_content)
                current_file = None # Reset
            else:
                # Start of block
                code_block_active = True
        elif code_block_active:
            buffer.append(line)

    # 6. Comment on Issue (Optional but nice)
    # We can use PyGithub to comment on the issue saying "I'm on it!" or "Done!"
    # For now, the PR creation in the workflow handles the notification.

if __name__ == "__main__":
    main()
