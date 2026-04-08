import { KnowledgeComposer } from "@/components/knowledge-composer";
import { getKnowledge } from "@/lib/api";

export default async function KnowledgePage() {
  const items = await getKnowledge();

  return (
    <div className="stack">
      <header className="page-header">
        <div>
          <span className="badge">AI knowledge base</span>
          <h2>База знаний</h2>
          <p>Все знания для AI заполняются вручную в `v1`: FAQ, услуги, акции, ToV и правила эскалации.</p>
        </div>
      </header>

      <section className="grid grid-2">
        <article className="panel">
          <h3>Добавить элемент</h3>
          <KnowledgeComposer />
        </article>
        <article className="panel">
          <h3>Текущий knowledge set</h3>
          <div className="stack">
            {items.length ? (
              items.map((item) => (
                <article className="message" key={item.id}>
                  <strong>{item.title}</strong>
                  <div className="mono">{item.kind}</div>
                  <p>{item.content}</p>
                </article>
              ))
            ) : (
              <div className="empty-state">Пока пусто. После добавления записей AI начнёт использовать их в retrieval.</div>
            )}
          </div>
        </article>
      </section>
    </div>
  );
}

