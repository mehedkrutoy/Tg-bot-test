from database.models import Base
from sqlalchemy import create_engine

def init_db():
    # Создаем подключение к базе данных
    engine = create_engine('sqlite:///database/bot.db')
    
    # Создаем все таблицы
    Base.metadata.create_all(engine)
    print("База данных успешно инициализирована")

if __name__ == "__main__":
    init_db() 