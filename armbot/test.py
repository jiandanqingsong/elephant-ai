import re

def count_python_code_lines(markdown_file):
    with open(markdown_file, 'r', encoding='utf-8') as file:
        content = file.read()

    pattern = r'```python\n(.*?)```'
    code_blocks = re.findall(pattern, content, re.DOTALL)
    
    total_lines = 0
    
    for block in code_blocks:
        lines = block.split('\n')
        for line in lines:
            stripped_line = line.strip()
            if stripped_line and not stripped_line.startswith('#'):
                total_lines += 1
    
    return total_lines

file_path = "test.md"
line_count = count_python_code_lines(file_path)
print(f"行数: {line_count}")