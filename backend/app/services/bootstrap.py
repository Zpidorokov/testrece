from __future__ import annotations

from datetime import datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import KnowledgeKind
from app.models import Branch, KnowledgeItem, Role, Service, StaffMember, StaffSchedule, StaffServiceMap


DEFAULT_ROLES = [
    ("owner", "Owner"),
    ("admin", "Admin"),
    ("manager", "Manager"),
    ("observer", "Observer"),
]


def ensure_default_roles(db: Session) -> None:
    existing_codes = set(db.scalars(select(Role.code)).all())
    created = False
    for code, name in DEFAULT_ROLES:
        if code not in existing_codes:
            db.add(Role(code=code, name=name, permissions_json={"scope": code}))
            created = True
    if created:
        db.commit()


DEMO_BRANCH = {
    "name": "Aster Beauty Lab",
    "address": "Санкт-Петербург, Петроградская сторона, Аптекарский проспект, 18",
    "timezone": "Europe/Moscow",
}

DEMO_SERVICES = [
    {
        "name": "Умный маникюр с покрытием gel polish",
        "description": "Комбинированный маникюр, выравнивание и однотонное покрытие. Включает мини-консультацию по домашнему уходу.",
        "duration_min": 120,
        "price_from": 3200,
        "price_to": 3800,
    },
    {
        "name": "Экспресс-педикюр Smart",
        "description": "Обработка стоп Smart-диском, педикюр пальцев и лёгкое увлажнение без покрытия.",
        "duration_min": 75,
        "price_from": 2900,
        "price_to": 3300,
    },
    {
        "name": "Архитектура бровей + окрашивание",
        "description": "Подбор формы, мягкая коррекция и окрашивание с естественным оттенком под тип внешности.",
        "duration_min": 60,
        "price_from": 1800,
        "price_to": 2200,
    },
    {
        "name": "Ламинирование ресниц",
        "description": "Подкручивание, питание составами и окрашивание ресниц для открытого взгляда без наращивания.",
        "duration_min": 75,
        "price_from": 2800,
        "price_to": 3200,
    },
    {
        "name": "Стрижка + укладка medium",
        "description": "Женская стрижка средней длины с мытьём, уходом и лёгкой текстурной укладкой.",
        "duration_min": 90,
        "price_from": 3400,
        "price_to": 4200,
    },
    {
        "name": "Окрашивание AirTouch consultation",
        "description": "Предзапись на большое окрашивание: консультация, тест-прядь и расчёт времени/стоимости.",
        "duration_min": 45,
        "price_from": 1500,
        "price_to": 1500,
    },
]

DEMO_STAFF = [
    {"full_name": "Марина Орлова", "specialization": "Маникюр и педикюр"},
    {"full_name": "Алиса Воронцова", "specialization": "Брови и ресницы"},
    {"full_name": "Елена Богданова", "specialization": "Стрижки и укладки"},
    {"full_name": "София Мельникова", "specialization": "Колорист и консультации"},
]

DEMO_KNOWLEDGE = [
    {
        "kind": KnowledgeKind.TONE_OF_VOICE.value,
        "title": "Тон общения Aster Beauty Lab",
        "content": (
            "Отвечай по-русски, тепло и уверенно, без фамильярности. Пиши короткими абзацами, без канцелярита. "
            "Главная задача: быстро понять запрос, назвать релевантную услугу, если нужно уточнить 1-2 вопроса, и мягко перевести к записи."
        ),
    },
    {
        "kind": KnowledgeKind.FAQ.value,
        "title": "Режим работы и локация",
        "content": (
            "Салон Aster Beauty Lab находится в Санкт-Петербурге на Петроградской стороне, Аптекарский проспект, 18. "
            "Работаем ежедневно с 10:00 до 22:00. Рядом есть городская парковка и 8 минут пешком от метро Петроградская."
        ),
    },
    {
        "kind": KnowledgeKind.POLICY.value,
        "title": "Правила записи и переноса",
        "content": (
            "Перенос и отмена без штрафа возможны не позднее чем за 6 часов до визита. На сложные окрашивания и большие комплексы "
            "может понадобиться предоплата 1000 рублей. Если клиент просит перенос, сначала уточни удобный день и диапазон времени."
        ),
    },
    {
        "kind": KnowledgeKind.PROMO.value,
        "title": "Акция для первого визита",
        "content": (
            "Для новых клиентов действует -10% на первый визит по будням с 12:00 до 16:00 на маникюр, педикюр, брови и ламинирование ресниц."
        ),
    },
    {
        "kind": KnowledgeKind.CONTRAINDICATION.value,
        "title": "Когда нужна эскалация человеку",
        "content": (
            "Если клиент пишет про аллергию, ожог, сильную боль, жалобу, возврат, беременность с противопоказаниями, медицинские вопросы "
            "или просит позвать администратора, сразу эскалируй диалог человеку."
        ),
    },
    {
        "kind": KnowledgeKind.SERVICE_INFO.value,
        "title": "Маникюр с покрытием",
        "content": (
            "Умный маникюр с покрытием gel polish длится около 2 часов и стоит 3200-3800 рублей. "
            "Подходит для аккуратного укрепления и носки 3-4 недели."
        ),
    },
    {
        "kind": KnowledgeKind.SERVICE_INFO.value,
        "title": "Педикюр Smart",
        "content": (
            "Экспресс-педикюр Smart длится 75 минут и стоит 2900-3300 рублей. "
            "Это быстрый вариант без покрытия, если нужно аккуратно обработать стопы и пальцы."
        ),
    },
    {
        "kind": KnowledgeKind.SERVICE_INFO.value,
        "title": "Брови и ресницы",
        "content": (
            "Архитектура бровей с окрашиванием занимает около часа, ламинирование ресниц 75 минут. "
            "Если клиент сомневается, предложи сначала брови как самый быстрый и понятный первый визит."
        ),
    },
    {
        "kind": KnowledgeKind.SERVICE_INFO.value,
        "title": "Стрижки и окрашивания",
        "content": (
            "Стрижка с укладкой medium занимает 90 минут и стоит 3400-4200 рублей. "
            "Для AirTouch и сложных окрашиваний сначала записываем на консультацию, где мастер рассчитывает бюджет и время."
        ),
    },
    {
        "kind": KnowledgeKind.OBJECTION_HANDLING.value,
        "title": "Если клиенту дорого",
        "content": (
            "Если клиент пишет, что дорого, спокойно объясни, что в стоимость входят материалы, работа мастера и консультация по уходу. "
            "После этого предложи более компактную услугу или время по акции."
        ),
    },
]


def ensure_demo_catalog(db: Session) -> None:
    branch = db.scalar(select(Branch).where(Branch.name == DEMO_BRANCH["name"]))
    if not branch:
        branch = Branch(**DEMO_BRANCH)
        db.add(branch)
        db.flush()

    existing_services = {item.name: item for item in db.scalars(select(Service)).all()}
    for item in DEMO_SERVICES:
        if item["name"] not in existing_services:
            db.add(Service(**item))
    db.flush()

    existing_staff = {item.full_name: item for item in db.scalars(select(StaffMember)).all()}
    for item in DEMO_STAFF:
        if item["full_name"] not in existing_staff:
            db.add(StaffMember(branch_id=branch.id, is_active=True, **item))
    db.flush()

    services = {item.name: item for item in db.scalars(select(Service)).all()}
    staff = {item.full_name: item for item in db.scalars(select(StaffMember)).all()}
    links = {
        "Марина Орлова": [
            "Умный маникюр с покрытием gel polish",
            "Экспресс-педикюр Smart",
        ],
        "Алиса Воронцова": [
            "Архитектура бровей + окрашивание",
            "Ламинирование ресниц",
        ],
        "Елена Богданова": [
            "Стрижка + укладка medium",
        ],
        "София Мельникова": [
            "Окрашивание AirTouch consultation",
            "Стрижка + укладка medium",
        ],
    }
    existing_maps = {
        (item.staff_id, item.service_id)
        for item in db.scalars(select(StaffServiceMap)).all()
    }
    for staff_name, service_names in links.items():
        staff_member = staff.get(staff_name)
        if not staff_member:
            continue
        for service_name in service_names:
            service = services.get(service_name)
            if not service:
                continue
            key = (staff_member.id, service.id)
            if key not in existing_maps:
                db.add(StaffServiceMap(staff_id=staff_member.id, service_id=service.id))
    db.flush()

    if not db.scalar(select(StaffSchedule.id).limit(1)):
        today = datetime.now().date()
        for offset in range(0, 21):
            day = today + timedelta(days=offset)
            if day.weekday() == 0:
                continue
            for staff_member in staff.values():
                start_hour = 10 if staff_member.full_name in {"Марина Орлова", "Алиса Воронцова"} else 11
                end_hour = 20 if staff_member.full_name != "София Мельникова" else 21
                db.add(
                    StaffSchedule(
                        staff_id=staff_member.id,
                        start_at=datetime.combine(day, time(hour=start_hour)),
                        end_at=datetime.combine(day, time(hour=end_hour)),
                        is_available=True,
                    )
                )
    db.flush()


def ensure_demo_knowledge(db: Session) -> None:
    existing_titles = set(db.scalars(select(KnowledgeItem.title)).all())
    for item in DEMO_KNOWLEDGE:
        if item["title"] not in existing_titles:
            db.add(KnowledgeItem(kind=item["kind"], title=item["title"], content=item["content"], metadata_json={}, is_active=True))
    db.flush()
