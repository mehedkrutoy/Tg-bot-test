from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, User, Payment, PromoCode, UsedPromoCode
from typing import Optional, Tuple
from datetime import datetime
import logging


# Настраиваем logger
logger = logging.getLogger(__name__)

# Создаем подключение к базе данных
engine = create_engine('sqlite:///database/bot.db')
# Создаем фабрику сессий
Session = sessionmaker(bind=engine)

def create_db():
    # Создаем все таблицы
    Base.metadata.create_all(engine)
    return Session()

async def get_user_balance(user_id: int) -> float:
    session = Session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        # Убедитесь, что пользователь найден и баланс не равен None
        return float(user.balance) if user and user.balance is not None else 0.0
    finally:
        session.close()

async def get_user_profile(user_id: int) -> Optional[Tuple[float, int]]:
    session = Session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user:
            balance = user.balance if user.balance is not None else 0.0
            total_referrals = user.total_referrals if user.total_referrals is not None else 0
            return float(balance), int(total_referrals)
        return None
    finally:
        session.close()

async def update_balance(user_id: int, amount: float) -> bool:
    session = Session()
    try:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user:
            user.balance = float(user.balance) + amount  # Корректно обновляем баланс
            session.commit()  # Сохраняем изменения
            return True
        return False
    except Exception as e:
        session.rollback()  # Откатываем изменения в случае ошибки
        logger.error(f"Ошибка при обновлении баланса: {e}")
        return False
    finally:
        session.close()

async def check_promo_code(code: str, user_id: int) -> Optional[dict]:
    """Проверяет, существует ли промокод и не использовал ли его пользователь"""
    session = Session()
    try:
        promo = session.query(PromoCode).filter(PromoCode.code == code).first()
        if not promo or promo.uses_left <= 0:
            return None
        
        # Проверяем, использовал ли пользователь этот промокод
        used = session.query(UsedPromoCode).filter(
            UsedPromoCode.user_id == user_id,
            UsedPromoCode.promo_code == code
        ).first()
        
        if used:
            return None  # Промокод уже использован пользователем
        
        return {
            'code': code,
            'amount': promo.amount,
            'is_percentage': promo.is_percentage
        }
    finally:
        session.close()

async def get_all_users():
    session = Session()
    users = session.query(User).all()
    session.close()
    return users 

async def create_promo_code(code: str, amount: float, uses: int, is_percentage: bool) -> bool:
    session = Session()
    try:
        promo = PromoCode(
            code=code,
            amount=amount,
            uses_left=uses,
            is_percentage=int(is_percentage)
        )
        session.add(promo)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при создании промокода: {e}")
        return False
    finally:
        session.close() 

async def use_promo_code(user_id: int, code: str) -> bool:
    """Записывает использование промокода пользователем"""
    session = Session()
    try:
        used_promo = UsedPromoCode(
            user_id=user_id,
            promo_code=code,
            used_at=datetime.now()
        )
        session.add(used_promo)
        session.commit()  # Сохраняем изменения
        return True
    except Exception as e:
        session.rollback()  # Откатываем изменения в случае ошибки
        logger.error(f"Ошибка при использовании промокода: {e}")
        return False
    finally:
        session.close()

async def create_payment(user_id: int, amount: float) -> bool:
    session = Session()
    try:
        payment = Payment(
            user_id=user_id,
            amount=amount,
            status='pending'
        )
        session.add(payment)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при создании платежа: {e}")
        return False
    finally:
        session.close()

async def update_payment_status(user_id: int, amount: float, status: str) -> bool:
    session = Session()
    try:
        payment = session.query(Payment).filter(
            Payment.user_id == user_id,
            Payment.amount == amount,
            Payment.status == 'pending'
        ).first()
        
        if payment:
            payment.status = status  # Обновляем статус напрямую
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при обновлении статуса платежа: {e}")
        return False
    finally:
        session.close() 

async def register_user(user_id: int, username: Optional[str], referrer_id: Optional[int] = None) -> bool:
    session = Session()
    try:
        # Проверяем, существует ли пользователь
        existing_user = session.query(User).filter(User.user_id == user_id).first()
        if existing_user:
            return False

        # Создаем нового пользователя
        new_user = User(
            user_id=user_id,
            username=username,
            referrer_id=referrer_id,
            balance=0.0
        )
        session.add(new_user)

        # Если есть реферер, увеличиваем его счетчик рефералов
        if referrer_id:
            referrer = session.query(User).filter(User.user_id == referrer_id).first()
            if referrer:
                referrer.total_referrals += 1  # Увеличиваем счетчик рефералов

        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при регистрации пользователя: {e}")
        return False
    finally:
        session.close()

async def get_user(user_id: int) -> Optional[User]:
    session = Session()
    try:
        return session.query(User).filter(User.user_id == user_id).first()
    finally:
        session.close() 

async def check_used_promo(user_id: int, promo_code: Optional[str]) -> bool:
    session = Session()

    if not promo_code:  # Добавляем проверку на None
        return False
        
    try:
        used_promo = session.query(UsedPromoCode).filter(
            UsedPromoCode.user_id == user_id,
            UsedPromoCode.promo_code == promo_code
        ).first()
        return bool(used_promo)
    finally:
        session.close()

async def has_used_any_promo(user_id: int) -> bool:
    session = Session()
    try:
        used_promo = session.query(UsedPromoCode).filter(
            UsedPromoCode.user_id == user_id
        ).first()
        return bool(used_promo)
    finally:
        session.close()

async def activate_promo_code(user_id: int, promo_code: str) -> Optional[float]:
    """Активирует промокод и начисляет бонус."""
    session = Session()
    try:
        promo = session.query(PromoCode).filter(PromoCode.code == promo_code).first()
        if not promo or promo.uses_left <= 0:
            return None
        
        # Записываем использование промокода
        used_promo = UsedPromoCode(
            user_id=user_id,
            promo_code=promo_code,
            used_at=datetime.now()
        )
        session.add(used_promo)
        
        # Уменьшаем количество использований
        promo.uses_left -= 1
        
        # Обновляем баланс пользователя
        user = session.query(User).filter(User.user_id == user_id).first()
        if user:
            user.balance += promo.amount  # Добавляем сумму на баланс
            session.commit()  # Сохраняем изменения
            return promo.amount
        
        return None
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при активации промокода: {e}")
        return None
    finally:
        session.close() 