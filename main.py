import psycopg2
from getpass import getpass
from datetime import datetime
from typing import List, Optional


class Database:
    """Класс для работы с базой данных PostgreSQL."""

    def __init__(self, db_name, user, password, host='localhost', port=5432):
        self.connection = psycopg2.connect(
            dbname=db_name, user=user, password=password, host=host, port=port
        )
        self.cursor = self.connection.cursor()

    def fetch_books(self) -> List[dict]:
        """Получить список всех книг."""
        self.cursor.execute("SELECT id, title, author, release_date, borrowed_by, borrow_date, return_date FROM lib")
        rows = self.cursor.fetchall()
        return [
            {
                "id": row[0],
                "title": row[1],
                "author": row[2],
                "release_date": row[3],
                "borrowed_by": row[4],
                "borrow_date": row[5],
                "return_date": row[6],
            }
            for row in rows
        ]

    def borrow_book(self, book_id: int, username: str, return_date: str):
        """Выдать книгу пользователю."""
        self.cursor.execute(
            "UPDATE lib SET borrowed_by = %s, borrow_date = %s, return_date = %s WHERE id = %s AND borrowed_by IS NULL",
            (username, datetime.now().date(), return_date, book_id),
        )
        self.connection.commit()
        if self.cursor.rowcount == 0:
            raise ValueError("Книга уже занята или не существует.")

    def return_book(self, book_id: int):
        """Вернуть книгу в библиотеку."""
        self.cursor.execute(
            "UPDATE lib SET borrowed_by = NULL, borrow_date = NULL, return_date = NULL WHERE id = %s",
            (book_id,),
        )
        self.connection.commit()

    def close(self):
        """Закрыть соединение с базой данных."""
        self.cursor.close()
        self.connection.close()

    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        """Аутентификация пользователя через таблицу roles."""
        self.cursor.execute(
            "SELECT role FROM roles WHERE username = %s AND password = %s",
            (username, password)
        )
        result = self.cursor.fetchone()
        return result[0] if result else None


class Observer:
    """Базовый класс наблюдателя."""
    def update(self, message: str):
        raise NotImplementedError("Метод 'update' должен быть реализован")


class Logger(Observer):
    """Наблюдатель для записи событий в лог."""
    def update(self, message: str):
        with open("library_log.txt", "a") as log_file:
            log_file.write(f"{datetime.now()}: {message}\n")


class LibraryApp:
    def __init__(self, db: Database):
        self.db = db
        self.role = None
        self.username = None
        self.observers = []  # Список наблюдателей

    def register_observer(self, observer: Observer):
        """Регистрация наблюдателя."""
        self.observers.append(observer)

    def notify_observers(self, message: str):
        """Уведомление всех наблюдателей."""
        for observer in self.observers:
            observer.update(message)

    def login(self):
        """Авторизация пользователя."""
        self.username = input("Введите логин: ")
        password = getpass("Введите пароль: ")

        self.role = self.db.authenticate_user(self.username, password)
        if self.role:
            print(f"Добро пожаловать, {self.username}! Ваша роль: {self.role}")
        else:
            print("Неверный логин или пароль.")
            exit()

    def show_books(self):
        books = self.db.fetch_books()
        print("\nСписок книг:")
        for book in books:
            status = f"Выдана {book['borrowed_by']} до {book['return_date']}" if book['borrowed_by'] else "Доступна"
            print(f"ID: {book['id']}, Название: {book['title']}, Автор: {book['author']}, Статус: {status}")

    def borrow_book(self):
        if self.role not in ("student", "librarian"):
            print("У вас нет доступа к выдаче книг.")
            return

        self.show_books()
        book_id = int(input("Введите ID книги, которую хотите взять: "))
        return_date = input("Введите дату возврата (YYYY-MM-DD): ")

        try:
            self.db.borrow_book(book_id, self.username, return_date)
            print("Книга успешно выдана!")
            self.notify_observers(f"Книга ID {book_id} выдана пользователю {self.username}.")
        except ValueError as e:
            print(e)

    def return_book(self):
        if self.role != "librarian":
            print("У вас нет доступа к возврату книг.")
            return

        self.show_books()
        book_id = int(input("Введите ID книги, которую хотите вернуть: "))

        try:
            self.db.return_book(book_id)
            print("Книга успешно возвращена!")
            self.notify_observers(f"Книга ID {book_id} возвращена в библиотеку.")
        except ValueError as e:
            print(e)

    def run(self):
        self.login()

        while True:
            print("\n1. Показать список книг")
            if self.role in ("student", "librarian"):
                print("2. Взять книгу")
            if self.role == "librarian":
                print("3. Вернуть книгу")
            print("0. Выйти")

            choice = input("Выберите действие: ")
            if choice == "1":
                self.show_books()
            elif choice == "2" and self.role in ("student", "librarian"):
                self.borrow_book()
            elif choice == "3" and self.role == "librarian":
                self.return_book()
            elif choice == "0":
                break
            else:
                print("Некорректный выбор. Попробуйте снова.")


if __name__ == "__main__":
    db = Database(db_name="test1", user="char", password="2103")
    try:
        app = LibraryApp(db)
        logger = Logger()
        app.register_observer(logger)
        app.run()
    finally:
        db.close()
