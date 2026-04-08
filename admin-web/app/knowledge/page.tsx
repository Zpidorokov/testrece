import { KnowledgeComposer } from "@/components/knowledge-composer";
import { KnowledgeListEditor } from "@/components/knowledge-list-editor";
import { getKnowledge } from "@/lib/api";

export default async function KnowledgePage() {
  const items = await getKnowledge();

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <span className="badge">AI-опора</span>
          <h2>База знаний</h2>
          <p>Редактируйте факты, услуги, правила и тон общения. Ассистент должен брать отсюда смысл, а не копировать абзацы дословно.</p>
        </div>
      </header>

      <section className="grid grid-2">
        <article className="panel">
          <h3>Новый блок</h3>
          <p className="panel-subtitle">Коротко, по фактам и без воды.</p>
          <KnowledgeComposer />
        </article>
        <article className="panel">
          <h3>Текущие блоки</h3>
          <p className="panel-subtitle">Можно редактировать, выключать и удалять прямо отсюда.</p>
          {items.length ? <KnowledgeListEditor items={items} /> : <div className="empty-state">Пока пусто. Добавь первые факты о салоне, услугах и правилах.</div>}
        </article>
      </section>
    </div>
  );
}
