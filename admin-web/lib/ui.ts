const dialogModeLabels: Record<string, string> = {
  auto: "Авто",
  manual: "Ручной",
};

const dialogStatusLabels: Record<string, string> = {
  new: "Новый",
  active: "Активный",
  waiting_client: "Ждем клиента",
  waiting_slot_selection: "Выбор окна",
  booked: "Записан",
  escalated: "Нужен человек",
  manual: "В ручном режиме",
  closed: "Закрыт",
  lost: "Потерян",
};

const bookingStatusLabels: Record<string, string> = {
  pending: "Ожидает",
  confirmed: "Подтверждена",
  rescheduled: "Перенесена",
  canceled_by_client: "Отменил клиент",
  canceled_by_staff: "Отменил салон",
  completed: "Завершена",
  no_show: "Не пришел",
};

const clientStatusLabels: Record<string, string> = {
  new: "Новый",
  consulting: "Консультация",
  interested: "Интересуется",
  booking_in_progress: "Подбираем запись",
  booked: "Записан",
  loyal: "Постоянный",
  vip: "VIP",
  problematic: "Сложный кейс",
  archived: "В архиве",
};

const knowledgeKindLabels: Record<string, string> = {
  faq: "FAQ и общие факты",
  service_info: "Услуги",
  promo: "Акции",
  policy: "Правила",
  contraindication: "Ограничения",
  tone_of_voice: "Тон общения",
  objection_handling: "Работа с возражениями",
  escalation_rule: "Когда звать человека",
};

const auditActionLabels: Record<string, string> = {
  client_created: "Создан клиент",
  dialog_created: "Создан диалог",
  notification_created: "Создано уведомление",
  booking_created: "Создана запись",
  admin_command_requested: "Открыта админ-панель",
  web_app_data_received: "Получены данные из mini app",
  ai_dispatch_failed: "Сбой AI-ответа",
  manual_mode_skip_ai: "AI пропущен из-за ручного режима",
  takeover: "Диалог забрал сотрудник",
  return_to_auto: "Диалог вернули AI",
};

const senderLabels: Record<string, string> = {
  client: "Клиент",
  ai: "Ассистент",
  staff: "Сотрудник",
  system: "Система",
};

function fromMap(map: Record<string, string>, value: string) {
  return map[value] ?? value;
}

export function formatDialogMode(value: string) {
  return fromMap(dialogModeLabels, value);
}

export function formatDialogStatus(value: string) {
  return fromMap(dialogStatusLabels, value);
}

export function formatBookingStatus(value: string) {
  return fromMap(bookingStatusLabels, value);
}

export function formatClientStatus(value: string) {
  return fromMap(clientStatusLabels, value);
}

export function formatKnowledgeKind(value: string) {
  return fromMap(knowledgeKindLabels, value);
}

export function formatAuditAction(value: string) {
  return fromMap(auditActionLabels, value);
}

export function formatSenderType(value: string) {
  return fromMap(senderLabels, value);
}
