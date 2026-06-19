
import hashlib
import re

import frontmatter
import shutil
import os

"""
This script will grab all markdown files in an obsidian vault that have "publish: true" in their frontmatter, and copy them to a hugo content directory, 
preserving the directory structure.
"""

# Path variables
VAULT_PATH = '../../garden/garden'
HUGO_PATH = '../content'
print_skipped = False
skip_directories = ['Private', 'Daily', 'Templates']

def public_posts(base_path):
    public_files = []
    for root, dirs, files in os.walk(base_path):
        for dir in dirs:
            if dir in skip_directories:
                print(f"Skipping directory {dir} because it's in the skip list.")
                dirs.remove(dir)  # This will prevent os.walk from going into this directory
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                post = frontmatter.load(file_path)
                if str(post.get('publish')).lower() == "true":
                    public_files.append(file_path)
    print(f"Found {len(public_files)} public files: {public_files}")
    return public_files

# builds a map of links to their target files, to be used for link rewriting. 
# The key is the post title as read in the frontmatter, and the value is the path to the file relative to the vault. 
def link_map(post_files):
    link_map = {}
    for file_path in post_files:
        post = frontmatter.load(file_path)
        title = post.get('title')
        if title:
            link_map[title] = os.path.relpath(file_path, VAULT_PATH)
        else:
            link_map[os.path.splitext(os.path.basename(file_path))[0]] = os.path.relpath(file_path, VAULT_PATH)
    print(f"Link map: {link_map}")
    return link_map

def sync_note(file_path, link_map):
    # Load the post object
    post = frontmatter.load(file_path)
    category = post.get('category', 'misc') # Defaults to 'misc'
    if category == 'misc' and post.get('catagory') is not None:
        print(f"Warning: 'catagory' is likely a typo in {file_path}. Using 'misc' as category.")
    file_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    dest_dir = os.path.join(HUGO_PATH, category)
    files = [file_path]

    # If the file is index, it's a hugo bundle, so we need to copy the whole directory
    if file_name.startswith('index'):
        dest_dir = os.path.join(HUGO_PATH, category, os.path.relpath(file_dir, VAULT_PATH))
        # dest_dir = os.path.join(HUGO_PATH, file_dir.replace(VAULT_PATH, '').lstrip('/'))
        for root, dirs, files2 in os.walk(file_dir):
            for file in files2:
                if file != file_name:  # Skip the index file itself
                    files.append(os.path.join(root, file))

    # read file to find wikilinks and replace them with hugo links. 
    # This is finding all links of the format [[link|alias]] or [[link]], and replacing them with [alias](path_to_file) or [link](path_to_file) respectively. 
    # The link is looked up in the link_map to find the target file, and then replaced with a hugo ref link.
    with open(file_path, 'r') as f:
        content = f.read()
        
        matches = re.findall(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', content)
        for match in matches:
            link = match[0]
            alias = match[1] if match[1] else link
            target_file = link_map.get(link)
            if target_file:
                hugo_link = f'[{alias}](/{"".join(target_file.split(os.sep))})'
                content = content.replace(match[0], hugo_link)
                print(f"Replaced link '{match[0]}' with '{hugo_link}' in {file_path}.")
            else:
                print(f"Warning: Link '{link}' in {file_path} not found in link map. Leaving as is.")
    #with open(file_path, 'w') as f:
    #    f.write(content)

    for file in files:
        dest_file = os.path.join(dest_dir, os.path.relpath(file, file_dir))
        # check if the file already exists
        if os.path.exists(dest_file):
            # check if file changed, by hash
            with open(file, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            with open(dest_file, 'rb') as f:
                dest_hash = hashlib.md5(f.read()).hexdigest()
            if file_hash == dest_hash:
                if print_skipped:
                    print(f"File {dest_file} already exists and is up to date. Skipping.")
                continue
            else:
                print(f"File {dest_file} has changed. Copying new version.")
        else:
            print (f"New file {file}. Copying to {dest_file}.")
            None
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
        shutil.copy2(file, dest_file)

if __name__ == "__main__":
    # Get all public posts
    public_notes = public_posts(VAULT_PATH)
    link_map = link_map(public_notes)
    for note in public_notes:
        sync_note(note, link_map)