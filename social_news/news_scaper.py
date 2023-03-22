"""Scrapes BBC homepage for cool articles."""
from urllib.request import urlopen
from bs4 import BeautifulSoup
import psycopg2
import psycopg2.extras
from dotenv import dotenv_values

BASE_URL = "http://bbc.co.uk"

config = dotenv_values('.env.production')
print(config)

def get_db_connection():
    """Establishes connection to psql database."""
    try:
        #connection = psycopg2.connect("dbname=social_news user='oliverjordan' host=localhost")
        connection = psycopg2.connect(user = config["DATABASE_USERNAME"],
                                      password = config["DATABASE_PASSWORD"],
                                      host = config["DATABASE_IP"],
                                      port = config["DATABASE_PORT"],
                                      database = config["DATABASE_NAME"])
        print("Connection successful.")
        return connection
    except:
        print("Error connecting to database.")

def get_html(url: str) -> str:
    """Gets html from a webpage"""
    with urlopen(url) as page:
        html_bytes = page.read()
        html = html_bytes.decode("utf_8")
        return html

def make_soup(url: str) -> BeautifulSoup:
    """Converts html into beautiful soup instance for paring."""
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    return soup

def get_story_info(soup: BeautifulSoup) -> list:
    """Extracts story title, url and metadata from bbc homepage."""
    story_blocks = soup.find_all('div', {'class': 'e1f5wbog8'})
    stories = []
    for block in story_blocks[:10]:
        try:
            url = block.find('a', {'class': 'e1f5wbog1'}).get('href')
            title = block.find('p', {'class': 'e1f5wbog5'}).get_text()
            tag = block.find('span', {'class': 'ecn1o5v1'}).get_text()
            stories.append([BASE_URL + url, title, tag])
        except Exception as err:
            print(err)
            print("Article information could not be found.")
            continue
    return stories

if __name__ == "__main__":
    bbc_soup = make_soup(BASE_URL)
    stories_data = get_story_info(bbc_soup)
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as curs:
        for story in stories_data:
            stories_query = "INSERT INTO stories (title, url) VALUES (%s, %s)"
            stories_params = (story[1], story[0])
            tags_query = """INSERT INTO tags (description)
                            SELECT %s WHERE NOT EXISTS (SELECT 1 FROM tags WHERE description = %s)"""
            tags_params = (story[2], story[2])
            metadata_query = """INSERT INTO metadata (story_id, tag_id)
                                SELECT stories.id, tags.id FROM stories, tags 
                                WHERE stories.url = %s AND tags.description = %s"""
            metadata_params = (story[0], story[2])
            curs.execute(stories_query, stories_params)
            curs.execute(tags_query, tags_params)
            curs.execute(metadata_query, metadata_params)
        conn.commit()
    print("Success!")
