"""Find out what unhappy customers complain about, from their review text.

Input:  mart_review_comments (built by scripts/build.py) and customer_segments
        (built by scripts/segment_customers.py)
Output: review_themes table in the database (one row per complaint per theme),
        outputs/tables/review_theme_validation.csv,
        outputs/tables/review_distinctive_terms.csv

Method:
  * Scope: 1-2 star reviews with a written comment. Comments are in Portuguese
    and are normalised first (lower case, accents and punctuation removed),
    so "não recebi", "Nao recebi" and "NÃO RECEBI!!" all match the same rule.
  * Themes: nine complaint themes defined by transparent keyword rules (THEMES
    below). A comment can mention several themes. Rules were written from an
    exploratory sample of comments and then checked once against a separate,
    hand-labelled random sample of 200 comments (data/labels), which gives
    each theme a precision and recall.
  * Distinctive terms: a data-driven cross-check that does not depend on the
    rules. Words and two-word phrases are compared between the two unhappy
    segments with weighted log-odds (Monroe, Colaresi and Quinn, 2008), which
    surfaces the phrases most typical of each group.

Usage:
    python scripts/analyse_reviews.py
"""
from pathlib import Path
import re
import sqlite3
import unicodedata

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "olist.db"
LABELS_PATH = ROOT / "data" / "labels" / "review_theme_labels.csv"
TABLES_DIR = ROOT / "outputs" / "tables"

SEGMENTS = ["Delivery-failure detractors", "Unhappy despite good delivery"]

W = r"(?:\w+ ){0,%d}"          # up to n intervening words, e.g. W % 2
# Words allowed between "nao" and its verb ("nao me responderam", "ainda nao
# foi"), so that "nao recomendo, recebi..." is not read as "not received".
NEG = r"(?:(?:ainda|me|nos|lhe|o|a|eu|tinha|tenho|havia|sequer|nem|foi|mais|nunca|se|deram|dao|teve|houve) ){0,3}"

# name: (label, group, patterns). Patterns run on normalised text.
THEMES = {
    "not_received": ("Not received (yet)", "1. Delivery", [
        r"\bnao " + NEG + r"(?:recebi|recebemos|recebido|chegou|chegaram|veio|entregaram|entregou)"
        r"\b(?! (?:nenhum\w* |qualquer |a |o )?(?:resposta|retorno|informac|satisfac|e ?mail|contato"
        r"|reembols|estorno|nota|codigo|posic|explicac|justificativ|aviso|mensag))",
        r"\bnao (?:foi|foram|tinha sido) entreg", r"\bnao entregue", r"\bnao chega nunca",
        r"\b(?:aguardo|aguardando|esperando|no aguardo) " + W % 2 + r"(?:entrega|produto|pedido|encomenda|mercadoria|chegada)",
        r"\bcade (?:o|a|meu|minha)\b", r"\bnada de (?:produto|chegar|entrega|receber)",
        r"\bnunca (?:chegou|recebi|foi entregue)", r"\bsem receber\b",
        r"\b(?:consta|constava|dado|aparece|esta|estava) (?:como )?(?:se fosse )?entregue",
        r"\bquando (?:vao|vai|sera) (?:entregar|chegar)", r"\bquando (?:vou|vamos|irei) receber",
        r"\bquero (?:o )?meu (?:produto|pedido)", r"\b(?:assim|quando|depois) que receber",
        r"\bextraviad", r"\b(?:devolvid\w*|retornou) (?:ao|para o|pro) remetente",
    ]),
    "late_or_slow": ("Late or slow delivery", "1. Delivery", [
        r"\batras", r"\bdemor", r"\blentid", r"\bentrega lenta", r"\bvagaros", r"\bpontualidade",
        r"\b(?:fora|alem|depois|apos) do prazo",
        r"\bprazo " + W % 3 + r"(?:passou|vencid\w*|venceu|expirou|esgot\w*|estour\w*|ultrapass\w*|acabou|terminou)",
        r"\b(?:passou|passaram|ultrapass\w*|exced\w*|estour\w*) " + W % 3 + r"(?:prazo|data prevista)",
        r"\b(?:mais de|quase) " + W % 1 + r"(?:\d+|um|dois|duas|tres|quinze|vinte|trinta) (?:dias|semanas|mes|meses)",
        r"\bnao " + W % 3 + r"(?:cumpr\w*|respeit\w*) " + W % 2 + r"prazo",
        r"\bprazo " + W % 3 + r"(?:longo|enorme|gigante|extenso|absurdo|muito grande|maior)",
        r"\b(?:previsao|prazo) " + W % 8 + r"(?:ate (?:agora|hoje|o momento)|e nada|ainda nao)",
        r"\besperei " + W % 3 + r"(?:dias|semanas|mes|meses)",
    ]),
    "collect_from_post_office": ("Had to collect from post office", "1. Delivery", [
        r"\b(?:retir\w*|busc\w*|peg\w*|apanh\w*) " + W % 4 + r"(?:correio|correios|agencia|deposito|transportadora)",
        r"\b(?:correio|correios|agencia) " + W % 3 + r"(?:para |pra )?(?:retirar|buscar|pegar|apanhar)",
        r"\bdisponivel (?:para retirada|na agencia|no correio|nos correios)",
    ]),
    "missing_items": ("Items or parts missing", "2. Order accuracy", [
        r"\b(?:recebi|recebemos|veio|vieram|chegou|chegaram|entregaram|entregue|enviaram|mandaram) "
        + W % 2 + r"(?:apenas|somente|so)\b",
        r"\b(?:apenas|somente|so) " + W % 2 + r"(?:recebi|recebemos|veio|vieram|chegou|chegaram|entregaram"
        r"|foi entregue|uma unidade|1 unidade|01 unidade)",
        r"\b(?:veio|vieram|chegou|ficou|esta|estao) faltando", r"\bfaltando\b", r"\bo unico que (?:veio|chegou)",
        r"\bfaltou " + W % 1 + r"(?:um|uma|1|01|dois|duas|o|a|os|as|pecas?|itens?|produtos?|parte|kit|unidade|vir|\d+)\b",
        r"\bfalta(?! de)\b " + W % 1 + r"(?:um|uma|1|01|dois|duas|o|a|os|as|peca|pecas|item|itens|produto|parte|kit|unidade)",
        r"\bincomplet",
        r"\bnao " + W % 2 + r"(?:recebi|recebemos|veio|chegou|chegaram) " + W % 1
        + r"(?:o outro|a outra|os outros|as outras|o segundo|a segunda|o restante|o resto)",
        r"\b(?:o|a) (?:outro|outra|segundo|segunda) " + W % 3 + r"nao (?:chegou|veio|recebi|foi entregue)",
        r"\b(?:um|uma) (?:dos|das) " + W % 2 + r"(?:nao (?:veio|chegou)|faltando)",
    ]),
    "wrong_item": ("Wrong item sent", "2. Order accuracy", [
        r"\berrad[oa]s?\b", r"\btrocad[oa]s?\b", r"\bno lugar\b",
        r"\b(?:veio|vieram) " + W % 2 + r"(?:outr[oa]s?|diferente)\b",
        r"\b(?:enviaram|mandaram|entregaram|recebi|chegou) " + W % 2
        + r"(?:outr[oa]s? (?:produto|modelo|cor|item|tamanho|coisa)|um produto diferente|produto diferente)",
        r"\b(?:enviaram|mandaram|veio) " + W % 3 + r"(?:compativel|similar|generico|paralelo)",
        r"\bdiferente do (?:que (?:eu )?(?:pedi|comprei|encomendei)|pedido|comprado|modelo)",
        r"\b(?:cor|cores|tamanho|modelo|numero|voltagem) " + W % 3 + r"(?:errad|diferente|trocad|nao confer)",
        r"\bnao (?:e|era) o (?:que|produto|modelo) " + W % 2 + r"(?:pedi|comprei|encomendei)",
    ]),
    "defective_or_damaged": ("Defective or damaged", "3. Product", [
        r"\bdefeit", r"\bquebrad", r"\bdanific", r"\bavari", r"\bamassad", r"\brasgad", r"\btrincad",
        r"\briscad", r"\briscos\b", r"\bestragad", r"\bvazand", r"\bvazad", r"\bfurad", r"\bmanchad",
        r"\bdescolad", r"\bqueimad", r"\bcorrompid", r"\bgarantia\b", r"\bsuj[oa]s?\b", r"\bviolad",
        r"\besfarel", r"\bdesmanch",
        r"\b(?:veio|chegou|vieram|chegaram) com " + W % 1 + r"(?:falha|falhas|problema|problemas|avaria)",
        r"\bnao " + W % 1 + r"(?:funciona|funcionou|funcionava|liga|ligou|acende|carrega|grava|le)\b",
        r"\bparou de funcionar", r"\bproblema (?:com|no|na) (?:o |a )?(?:aparelho|produto|equipamento)",
    ]),
    "poor_quality_or_not_as_described": ("Poor quality or not as described", "3. Product", [
        r"(?<!boa )(?<!otima )(?<!excelente )(?<!alta )(?<!de )(?<!mesma )\bqualidade\b",
        r"\bfrage(?:l|is)\b", r"\bvagabund", r"\bporcaria", r"\blixo\b", r"\bfalsificad",
        r"\bfals[oa]s?\b", r"\bpirat", r"\bimitac", r"\bmal acabad",
        r"\bproduto (?:falso|pirata)", r"\breplica\b", r"\bnao (?:e )?original", r"\bxing ling",
        r"\bmaterial " + W % 2 + r"(?:ruim|fraco|fino|pessimo|horrivel|vagabundo|inferior|barato)",
        r"\b(?:muito|super|bem|extremamente) (?:fino|fina|finos|finas|fraco|fraca|simples|pequeno|pequena|duro|dura)\b",
        r"\bdiferente " + W % 2 + r"(?:da|do|das|dos) (?:foto|imagem|anuncio|anunciad\w*|descri\w*|site|propaganda)",
        r"\b(?:descri\w*|anuncio|foto|fotos|imagem) " + W % 4
        + r"(?:nao (?:condiz|corresponde|confere|bate|e igual)|diferente|engan)",
        r"\bpropaganda enganosa", r"\babaixo d[ao] (?:esperad|expectativ)",
        r"\bnao (?:atendeu|atende|correspond\w*) " + W % 2 + r"(?:expectativ|esperad)",
        r"\bnao (?:era|e) (?:o )?(?:que|como) (?:eu )?esperava", r"\bnao gostei\b", r"\bdecepcion",
        r"\bnao (?:serve|serviu|coube|cabe|encaix\w*|ajust\w*)\b", r"\bdesmont",
        r"\bproduto " + W % 2 + r"(?:ruim|pessimo|horrivel|fraco)\b",
    ]),
    "no_response_from_seller": ("No response or poor support", "4. Service", [
        r"\bsem (?:nenhuma |nenhum |qualquer )?(?:resposta|retorno|satisfac|posicionamento|explicac"
        r"|justificativ|informac|previsao|solucao)",
        r"\bnenhum\w* " + W % 1 + r"(?:resposta|retorno|satisfac|posicionamento|explicac|justificativ"
        r"|informac|esclarecimento|solucao|posic)",
        r"\bnao " + NEG + r"(?:respond\w*|retorn\w*)\b", r"\bzero resposta",
        r"\bnao (?:obtive|tive|recebi|deram|dao|deu) " + W % 1 + r"(?:resposta|retorno|satisfac|explicac)",
        r"\bninguem " + W % 1 + r"(?:respond|atend|retorn|resolv)",
        r"\b(?:pessimo|mau|ruim|horrivel|falta de) atendimento", r"\batendimento " + W % 1 + r"(?:pessimo|ruim|horrivel|precario)",
        r"\bnao consig\w* " + W % 3 + r"(?:falar|contato|contatar|resolver|reclamar|registrar)",
        r"\bdificil " + W % 1 + r"contato", r"\bdescaso\b",
        r"\bfalta de " + W % 1 + r"(?:informac|respeito|consideracao|compromisso|comunicac|satisfac)",
        r"\bnem " + W % 3 + r"(?:satisfac|resposta|retorno|explicac)",
    ]),
    "refund_return_or_exchange": ("Wants refund, return or exchange", "4. Service", [
        r"\bdevol", r"\breembols", r"\bressarc", r"\bestorn", r"\bdinheiro de volta",
        r"\bmeu dinheiro\b", r"\btroc(?:a|ar|asse|ou|que|quem)\b", r"\bcancelar\b", r"\bcancelamento\b",
    ]),
}

# Portuguese function words removed before comparing vocabularies. Negations
# and quantity words ("nao", "so", "apenas", "um") are deliberately kept:
# they carry the meaning of complaints such as "so recebi um".
STOPWORDS = """a o as os e de do da dos das em no na nos nas para pra pro por com que se me
meu minha meus minhas eu voce voces ele ela eles elas isso esse essa este esta isto
foi ser ter tem tinha mais mas ou como muito muita ja ainda ate ao aos sua seu
the lannister stark targaryen baratheon martell tully tyrell americanas americana loja site""".split()


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text).lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tag_themes(text: pd.Series) -> pd.DataFrame:
    flags = pd.DataFrame(index=text.index)
    for name, (_, _, patterns) in THEMES.items():
        regex = re.compile("|".join(f"(?:{p})" for p in patterns))
        flags[name] = text.str.contains(regex).astype(int)
    # Precedence: "nao recebi o outro" is a missing item, not a missing order,
    # and a customer who collected the parcel did receive it.
    flags.loc[(flags["missing_items"] == 1) | (flags["collect_from_post_office"] == 1),
              "not_received"] = 0
    return flags


def validate(complaints: pd.DataFrame) -> pd.DataFrame:
    """Compare rule output with the hand-labelled sample."""
    labels = pd.read_csv(LABELS_PATH)
    pred = labels[["order_id"]].merge(complaints, on="order_id", how="left")
    assert pred[list(THEMES)].notna().all().all(), "labelled order missing from complaints"
    in_delivery = (labels["cluster_segment"] == SEGMENTS[0]).to_numpy()
    rows = []
    for name, (label, group, _) in THEMES.items():
        y, p = labels[name].to_numpy(), pred[name].to_numpy()
        tp = int(((y == 1) & (p == 1)).sum())
        fp = int(((y == 0) & (p == 1)).sum())
        fn = int(((y == 1) & (p == 0)).sum())
        precision = tp / (tp + fp) if tp + fp else np.nan
        recall = tp / (tp + fn) if tp + fn else np.nan
        rows.append({
            "theme_group": group, "theme": label,
            "hand_labelled": int(y.sum()), "rule_tagged": int(p.sum()), "agreed": tp,
            "precision": round(precision, 2), "recall": round(recall, 2),
            "f1": round(2 * precision * recall / (precision + recall), 2) if tp else 0.0,
            # share of each segment's sampled comments with the theme, by hand
            "hand_pct_delivery_failure": round(100 * y[in_delivery].mean(), 1),
            "hand_pct_good_delivery": round(100 * y[~in_delivery].mean(), 1),
        })
    return pd.DataFrame(rows)


def distinctive_terms(complaints: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Weighted log-odds with an informative Dirichlet prior (document counts)."""
    vec = CountVectorizer(ngram_range=(1, 2), min_df=15, binary=True, stop_words=STOPWORDS)
    X = vec.fit_transform(complaints["text"])
    terms = vec.get_feature_names_out()
    in_a = (complaints["cluster_segment"] == SEGMENTS[0]).to_numpy()
    y_a = np.asarray(X[in_a].sum(axis=0)).ravel()
    y_b = np.asarray(X[~in_a].sum(axis=0)).ravel()
    prior = (y_a + y_b) / (y_a + y_b).sum() * 500        # prior worth 500 term counts
    n_a, n_b, a0 = y_a.sum(), y_b.sum(), prior.sum()
    delta = (np.log((y_a + prior) / (n_a + a0 - y_a - prior))
             - np.log((y_b + prior) / (n_b + a0 - y_b - prior)))
    z = delta / np.sqrt(1 / (y_a + prior) + 1 / (y_b + prior))
    table = pd.DataFrame({
        "term": terms, "z_score": z.round(1),
        f"pct_{SEGMENTS[0]}": (100 * y_a / in_a.sum()).round(1),
        f"pct_{SEGMENTS[1]}": (100 * y_b / (~in_a).sum()).round(1),
    })
    top_a = table.nlargest(top_n, "z_score").assign(more_typical_of=SEGMENTS[0])
    top_b = table.nsmallest(top_n, "z_score").assign(more_typical_of=SEGMENTS[1])
    out = pd.concat([top_a, top_b])
    return out[["more_typical_of", "term", "z_score"] + [c for c in out.columns if c.startswith("pct_")]]


def main() -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        reviews = pd.read_sql_query("""
            select c.order_id, c.review_title, c.review_message, c.is_delivered,
                   s.cluster_segment
            from mart_review_comments c
            left join customer_segments s on s.customer_unique_id = c.customer_unique_id
            where c.review_score <= 2
        """, con)
        reviews["text"] = (reviews["review_title"].fillna("") + " "
                           + reviews["review_message"]).map(normalise)
        flags = tag_themes(reviews["text"])
        tagged = pd.concat([reviews, flags], axis=1)

        long = tagged.melt(id_vars="order_id", value_vars=list(THEMES), var_name="theme_key")
        long = long[long["value"] == 1].drop(columns="value")
        long["theme"] = long["theme_key"].map(lambda k: THEMES[k][0])
        long["theme_group"] = long["theme_key"].map(lambda k: THEMES[k][1])
        long.to_sql("review_themes", con, if_exists="replace", index=False)
        con.execute("create index if not exists idx_rt_order on review_themes(order_id)")

    complaints = tagged[(tagged["is_delivered"] == 1) & tagged["cluster_segment"].isin(SEGMENTS)]
    validation = validate(complaints)
    validation.to_csv(TABLES_DIR / "review_theme_validation.csv", index=False)
    terms = distinctive_terms(complaints)
    terms.to_csv(TABLES_DIR / "review_distinctive_terms.csv", index=False)

    print(f"Tagged {len(reviews):,} low-score comments "
          f"({(flags.sum(axis=1) > 0).mean():.0%} match at least one theme); "
          f"{len(long):,} theme mentions written to review_themes")
    print("\nRules vs hand-labelled sample (200 comments):")
    print(validation.drop(columns="theme_group").to_string(index=False))
    print("\nMost distinctive terms:")
    print(terms.to_string(index=False))


if __name__ == "__main__":
    main()
