CREATE_SQLITE = """CREATE TABLE IF NOT EXISTS "user_account" (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	email TEXT NOT NULL CHECK (LENGTH(email) <= 50) UNIQUE,
	first_name TEXT NOT NULL CHECK (LENGTH(first_name) <= 20),
	last_name TEXT NOT NULL CHECK (LENGTH(last_name) <= 20), 
	password TEXT NOT NULL, 
	is_active BOOLEAN DEFAULT 1 NOT NULL, 
	role TEXT DEFAULT 'student' NOT NULL CHECK (role IN ('student', 'admin', 'external') AND LENGTH(role) <= 20)
);

CREATE TABLE IF NOT EXISTS "category" (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	name TEXT NOT NULL CHECK (LENGTH(name) <= 20) UNIQUE, 
    added_by_id INTEGER NOT NULL,
    FOREIGN KEY(added_by_id) REFERENCES user_account (id)
);

CREATE TABLE IF NOT EXISTS "book" (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	title TEXT NOT NULL CHECK (LENGTH(title) <= 100), 
	author TEXT NOT NULL CHECK (LENGTH(author) <= 50), 
	isbn TEXT NOT NULL CHECK (LENGTH(isbn) <= 25) UNIQUE, 
	category_id INTEGER NOT NULL, 
	original_quantity INTEGER DEFAULT '1' NOT NULL, 
	current_quantity INTEGER DEFAULT '1' NOT NULL, 
	date_added DATETIME NOT NULL, 
	added_by_id INTEGER NOT NULL, 
	is_available BOOLEAN DEFAULT 1 NOT NULL,
    location TEXT CHECK (LENGTH(location) <= 20) NOT NULL DEFAULT 'shelf', 
	FOREIGN KEY(category_id) REFERENCES category (id), 
	FOREIGN KEY(added_by_id) REFERENCES user_account (id)
);

CREATE TABLE IF NOT EXISTS "borrow" (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	book_id INTEGER NOT NULL, 
	borrowed_by_id INTEGER NOT NULL, 
	given_by_id INTEGER NOT NULL, 
	received_by_id INTEGER, 
	borrow_date DATETIME NOT NULL, 
	due_date DATETIME NOT NULL, 
	return_date DATETIME, 
	comments TEXT, 
	is_returned BOOLEAN DEFAULT 0 NOT NULL, 
	FOREIGN KEY(book_id) REFERENCES book (id), 
	FOREIGN KEY(borrowed_by_id) REFERENCES user_account (id), 
	FOREIGN KEY(given_by_id) REFERENCES user_account (id), 
	FOREIGN KEY(received_by_id) REFERENCES user_account (id)
);

CREATE TABLE IF NOT EXISTS "fine" (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	borrow_id INTEGER NOT NULL UNIQUE, 
	amount REAL NOT NULL, 
	paid BOOLEAN DEFAULT 0 NOT NULL, 
	date_created DATETIME NOT NULL, 
	date_paid DATETIME, 
	payment_method TEXT CHECK (LENGTH(payment_method) <= 15), 
	transaction_id TEXT CHECK (LENGTH(transaction_id) <= 100) UNIQUE, 
	collected_by_id INTEGER,
	FOREIGN KEY(borrow_id) REFERENCES borrow (id), 
	FOREIGN KEY(collected_by_id) REFERENCES user_account (id)
);
"""


CREATE_POSTGRES = """CREATE TABLE IF NOT EXISTS "user_account" (
	id SERIAL PRIMARY KEY,
	email VARCHAR(50) NOT NULL,
	first_name VARCHAR(20) NOT NULL,
	last_name VARCHAR(20) NOT NULL, 
	password VARCHAR NOT NULL, 
	is_active BOOLEAN DEFAULT '1' NOT NULL, 
	role VARCHAR(20) DEFAULT 'student' NOT NULL CHECK (role IN ('student', 'admin', 'external')),
	UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS "category" (
	id SERIAL PRIMARY KEY,
	name VARCHAR(20) NOT NULL, 
    added_by_id INTEGER NOT NULL,
	UNIQUE (name),
    FOREIGN KEY(added_by_id) REFERENCES user_account (id)
);

CREATE TABLE IF NOT EXISTS "book" (
	id SERIAL PRIMARY KEY,
	title VARCHAR(100) NOT NULL, 
	author VARCHAR(50) NOT NULL, 
	isbn VARCHAR(25) NOT NULL, 
	category_id INTEGER NOT NULL, 
	original_quantity INTEGER DEFAULT '1' NOT NULL, 
	current_quantity INTEGER DEFAULT '1' NOT NULL, 
	date_added TIMESTAMP NOT NULL, 
	added_by_id INTEGER NOT NULL, 
	is_available BOOLEAN DEFAULT '1' NOT NULL, 
    location VARCHAR(20) DEFAULT 'shelf' NOT NULL,
	UNIQUE (isbn), 
	FOREIGN KEY(category_id) REFERENCES category (id), 
	FOREIGN KEY(added_by_id) REFERENCES user_account (id)
);

CREATE TABLE IF NOT EXISTS "borrow" (
	id SERIAL PRIMARY KEY,
	book_id INTEGER NOT NULL, 
	borrowed_by_id INTEGER NOT NULL, 
	given_by_id INTEGER NOT NULL, 
	received_by_id INTEGER, 
	borrow_date TIMESTAMP NOT NULL, 
	due_date TIMESTAMP NOT NULL, 
	return_date TIMESTAMP, 
	comments VARCHAR, 
	is_returned BOOLEAN DEFAULT '0' NOT NULL, 
	FOREIGN KEY(book_id) REFERENCES book (id), 
	FOREIGN KEY(borrowed_by_id) REFERENCES user_account (id), 
	FOREIGN KEY(given_by_id) REFERENCES user_account (id), 
	FOREIGN KEY(received_by_id) REFERENCES user_account (id)
);

CREATE TABLE IF NOT EXISTS "fine" (
	id SERIAL PRIMARY KEY,
	borrow_id INTEGER NOT NULL, 
	amount FLOAT NOT NULL, 
	paid BOOLEAN DEFAULT '0' NOT NULL, 
	date_created TIMESTAMP NOT NULL, 
	date_paid TIMESTAMP, 
	payment_method VARCHAR(15), 
	transaction_id VARCHAR(100), 
	collected_by_id INTEGER,
	FOREIGN KEY(borrow_id) REFERENCES borrow (id), 
	FOREIGN KEY(collected_by_id) REFERENCES user_account (id),
	UNIQUE (transaction_id),
    UNIQUE (borrow_id)
);
"""
