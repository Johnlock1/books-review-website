import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


def main():
    f = open("books.csv")
    reader = csv.reader(f)
    next(reader, None)  # skip the headers

    # iterate throught each row in csv file
    for isbn, title, author, year in reader:

        # add author into authors table if author doesn't exists in table
        if db.execute("SELECT * FROM authors WHERE name=:name", {"name": author}).rowcount == 0:
            db.execute("INSERT INTO authors (name) VALUES (:name)", {"name": author})

            print(f"Added author {author}.")

        # get author_id
        result = db.execute("SELECT id FROM authors WHERE name=:name",
                            {"name": author}).fetchone()
        author_id = result[0]

        print("\n")
        print(author_id)
        print("\n")

        # intert book into books table
        db.execute("INSERT INTO books (isbn, title, author_id, year) \
            VALUES (:isbn, :title, :author_id, :year)",
                   {"isbn": isbn, "title": title, "author_id": author_id, "year": int(year)})

        print(f"Added book {isbn}, {title} of {author} published in {year}.")

    db.commit()
    f.close()


if __name__ == "__main__":
    main()
