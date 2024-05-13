import os

def replace_static_with_image(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace "static/" with "../image/"
    new_content = content.replace('../images/', '/images/')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def main():
    # Specify the directory containing your blog files
    blog_directory = './_posts'

    # Iterate through all files in the directory
    for filename in os.listdir(blog_directory):
        if filename.endswith('.md'):  # Process only markdown files
            file_path = os.path.join(blog_directory, filename)
            replace_static_with_image(file_path)
            print(f"Replaced 'static/' with '../images/' in {filename}")

if __name__ == "__main__":
    main()
