import json
import logging
import os
from datetime import date
from typing import Any, Dict, List, Optional

import asyncpg

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с PostgreSQL"""

    def __init__(self):
        self.pool = None
        self.db_url = os.getenv("DATABASE_URL")

    async def connect(self):
        """Подключение к базе данных"""
        try:
            if not self.db_url:
                # Формируем URL из переменных окружения
                host = os.getenv("DB_HOST", "localhost")
                port = os.getenv("DB_PORT", "5432")
                dbname = os.getenv("DB_NAME", "yourlifepilot")
                user = os.getenv("DB_USER", "yourlifepilot_user")
                password = os.getenv("DB_PASSWORD", "")

                self.db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

            # Создаем пул соединений
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=5,
                max_size=20,
                command_timeout=60,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
            )

            logger.info("✅ Подключено к PostgreSQL")

            # Проверяем соединение
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
                logger.info("✅ Проверка соединения успешна")

        except Exception as e:
            logger.error(f"❌ Ошибка подключения к БД: {e}")
            raise

    async def close(self):
        """Закрытие соединения с БД"""
        if self.pool:
            await self.pool.close()
            logger.info("✅ Соединение с PostgreSQL закрыто")

    # =================================================
    # ПОЛЬЗОВАТЕЛИ
    # =================================================

    async def save_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Сохраняет или обновляет пользователя"""
        try:
            async with self.pool.acquire() as conn:
                # Проверяем существование пользователя
                exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM users WHERE user_id = $1)", user_id)

                if exists:
                    # Обновляем существующего пользователя
                    await conn.execute(
                        """
                        UPDATE users SET
                            username = $2,
                            first_name = $3,
                            last_name = $4,
                            onboarding_complete = $5,
                            scenario = $6::jsonb,
                            answers = $7::jsonb,
                            last_active = CURRENT_TIMESTAMP
                        WHERE user_id = $1
                    """,
                        user_id,
                        user_data.get("username", ""),
                        user_data.get("first_name", ""),
                        user_data.get("last_name", ""),
                        user_data.get("onboarding_complete", False),
                        json.dumps(user_data.get("scenario", [])),
                        json.dumps(user_data.get("answers", {})),
                    )
                    logger.info(f"✅ Пользователь {user_id} обновлен в БД")
                else:
                    # Создаем нового пользователя
                    await conn.execute(
                        """
                        INSERT INTO users (
                            user_id, username, first_name, last_name,
                            onboarding_complete, scenario, answers,
                            created_at, last_active
                        ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, 
                                 CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                        user_id,
                        user_data.get("username", ""),
                        user_data.get("first_name", ""),
                        user_data.get("last_name", ""),
                        user_data.get("onboarding_complete", False),
                        json.dumps(user_data.get("scenario", [])),
                        json.dumps(user_data.get("answers", {})),
                    )
                    logger.info(f"✅ Новый пользователь {user_id} создан в БД")

                return True

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения пользователя {user_id}: {e}")
            return False

    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Получает данные пользователя"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка получения пользователя {user_id}: {e}")
            return None

    async def get_all_users(self) -> List[Dict]:
        """Получает всех пользователей"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM users ORDER BY created_at DESC")
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Ошибка получения всех пользователей: {e}")
            return []

    async def get_onboarded_users(self) -> List[Dict]:
        """Получает пользователей, прошедших онбординг"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM users WHERE onboarding_complete = TRUE")
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Ошибка получения onboarded пользователей: {e}")
            return []

    # =================================================
    # СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ (STREAKS)
    # =================================================

    async def save_user_stats(self, user_id: str, stats: Dict[str, Any]) -> bool:
        """Сохраняет статистику пользователя"""
        try:
            async with self.pool.acquire() as conn:
                # Проверяем существование
                exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM user_stats WHERE user_id = $1)", user_id)

                # Подготовка данных
                last_action_date = stats.get('last_action_date', {})

                if exists:
                    # Обновляем
                    await conn.execute(
                        """
                        UPDATE user_stats SET
                            morning_streak = $2,
                            morning_skip_streak = $3,
                            evening_streak = $4,
                            evening_skip_streak = $5,
                            day_stress_streak = $6,
                            day_stress_skip_streak = $7,
                            last_morning_date = $8,
                            last_evening_date = $9,
                            last_stress_date = $10,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = $1
                    """,
                        user_id,
                        stats.get('morning_streak', 0),
                        stats.get('morning_skip_streak', 0),
                        stats.get('evening_streak', 0),
                        stats.get('evening_skip_streak', 0),
                        stats.get('day_stress_streak', 0),
                        stats.get('day_stress_skip_streak', 0),
                        last_action_date.get('morning'),
                        last_action_date.get('evening'),
                        last_action_date.get('day_stress'),
                    )
                else:
                    # Создаем
                    await conn.execute(
                        """
                        INSERT INTO user_stats (
                            user_id, morning_streak, morning_skip_streak,
                            evening_streak, evening_skip_streak,
                            day_stress_streak, day_stress_skip_streak,
                            last_morning_date, last_evening_date, last_stress_date
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                        user_id,
                        stats.get('morning_streak', 0),
                        stats.get('morning_skip_streak', 0),
                        stats.get('evening_streak', 0),
                        stats.get('evening_skip_streak', 0),
                        stats.get('day_stress_streak', 0),
                        stats.get('day_stress_skip_streak', 0),
                        last_action_date.get('morning'),
                        last_action_date.get('evening'),
                        last_action_date.get('day_stress'),
                    )

                logger.info(f"✅ Статистика пользователя {user_id} сохранена")
                return True

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения статистики {user_id}: {e}")
            return False

    async def get_user_stats(self, user_id: str) -> Optional[Dict]:
        """Получает статистику пользователя"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM user_stats WHERE user_id = $1", user_id)
                if row:
                    data = dict(row)
                    # Преобразуем в формат, ожидаемый кодом
                    return {
                        'morning_streak': data['morning_streak'],
                        'morning_skip_streak': data['morning_skip_streak'],
                        'evening_streak': data['evening_streak'],
                        'evening_skip_streak': data['evening_skip_streak'],
                        'day_stress_streak': data['day_stress_streak'],
                        'day_stress_skip_streak': data['day_stress_skip_streak'],
                        'last_action_date': {
                            'morning': data['last_morning_date'],
                            'evening': data['last_evening_date'],
                            'day_stress': data['last_stress_date'],
                        },
                    }
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики {user_id}: {e}")
            return None

    # =================================================
    # ИСТОРИЯ НАСТРОЕНИЯ
    # =================================================

    async def save_mood(self, user_id: str, feeling: str, note: str = "") -> bool:
        """Сохраняет запись о настроении"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO mood_history (user_id, feeling, note, created_at)
                    VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                """,
                    user_id,
                    feeling,
                    note,
                )

                logger.info(f"✅ Настроение '{feeling}' сохранено для {user_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения настроения: {e}")
            return False

    async def get_mood_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Получает историю настроения пользователя"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT feeling, note, created_at
                    FROM mood_history
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """,
                    user_id,
                    limit,
                )

                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории настроения: {e}")
            return []

    # =================================================
    # ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ
    # =================================================

    async def save_action(self, user_id: str, action_type: str, action_result: str, details: Dict = None) -> bool:
        """Сохраняет действие пользователя"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO user_actions (user_id, action_type, action_result, details)
                    VALUES ($1, $2, $3, $4::jsonb)
                """,
                    user_id,
                    action_type,
                    action_result,
                    json.dumps(details or {}),
                )

                logger.info(f"✅ Действие {action_type}/{action_result} сохранено")
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения действия: {e}")
            return False

    # =================================================
    # СТАТИСТИКА
    # =================================================

    async def get_stats(self) -> Dict[str, Any]:
        """Получает общую статистику"""
        try:
            async with self.pool.acquire() as conn:
                # Общее количество пользователей
                total_users = await conn.fetchval("SELECT COUNT(*) FROM users")

                # Прошедшие онбординг
                onboarded = await conn.fetchval("SELECT COUNT(*) FROM users WHERE onboarding_complete = TRUE")

                # Активные сегодня
                today = date.today()
                active_today = await conn.fetchval(
                    """
                    SELECT COUNT(DISTINCT user_id) 
                    FROM user_actions 
                    WHERE created_at::date = $1
                """,
                    today,
                )

                # Статистика по настроениям за 7 дней
                mood_stats = await conn.fetch(
                    """
                    SELECT feeling, COUNT(*) as count
                    FROM mood_history
                    WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
                    GROUP BY feeling
                    ORDER BY count DESC
                """
                )

                # Средние streak'и
                avg_streaks = await conn.fetchrow(
                    """
                    SELECT 
                        AVG(morning_streak) as avg_morning,
                        AVG(evening_streak) as avg_evening,
                        AVG(day_stress_streak) as avg_stress
                    FROM user_stats
                """
                )

                return {
                    "total_users": total_users,
                    "onboarded_users": onboarded,
                    "completion_rate": round((onboarded / total_users * 100) if total_users > 0 else 0, 1),
                    "active_today": active_today,
                    "mood_stats": {row['feeling']: row['count'] for row in mood_stats},
                    "avg_streaks": {
                        "morning": round(avg_streaks['avg_morning'] or 0, 1),
                        "evening": round(avg_streaks['avg_evening'] or 0, 1),
                        "stress": round(avg_streaks['avg_stress'] or 0, 1),
                    },
                }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {"error": str(e)}


# Создаем глобальный экземпляр БД
db = Database()
