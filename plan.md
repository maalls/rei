# Refactor Plan: src/langgraph/app.py

## Objectif
Decouper src/langgraph/app.py en modules plus petits, testables, et lisibles, sans changer le comportement fonctionnel.

## Principes
- Conserver la logique existante et faire un refactor progressif.
- Extraire d'abord les elements stables (schemas, state, utils).
- Garder un point d'entree minimal dans src/langgraph/app.py.
- Preserver le format des messages et la cle de thread (thread_id = chat_id).

## Structure cible

```text
src/langgraph/
	app.py
	state.py
	schemas.py
	message_utils.py
	graph_builder.py
	nodes/
		__init__.py
		group_intent.py
		classify_intent.py
		rag.py
		handover.py
		chat.py
		code.py
		chikichiki.py
```

## Responsabilites par fichier

### app.py
- Classe LangGraphApp minimale.
- Initialise dependances (llm, vector_store, admin_bot).
- Appelle le builder de graphe.
- Expose invoke, store_new_knowledge, format_request_reply si necessaire.

### state.py
- State (TypedDict) pour le graphe.

### schemas.py
- Modeles Pydantic:
	- IntentClassifier
	- GroupIntent
	- RewrittenQuery
	- Response
	- CouldReplyClassifier
	- ChikiChikiClassifier
	- HumanRequest

### message_utils.py
- Fonctions utilitaires:
	- normalize_text
	- to_chat_line
	- to_llm_message
	- format_response

### nodes/*.py
- Un module par famille de noeuds:
	- group_intent.py: decision d'adressage
	- classify_intent.py: classification intention + traitement request_reply
	- rag.py: rewrite_knowledge_query, prompt_llm_rag
	- handover.py: handover vers admin
	- chat.py: reponse chat
	- code.py: agent code
	- chikichiki.py: detection + reponse speciale

### graph_builder.py
- Construction du StateGraph.
- Ajout des noeuds et des transitions conditionnelles.
- Compilation avec checkpointer.

## Contrats a figer
- Format message JSON:
	- chat_id
	- text
	- from.username
	- date
	- timestamp
- thread_id toujours derive de chat_id.
- Les noeuds retournent uniquement des partial updates compatibles LangGraph.

## Plan de migration (safe)

### Etape 1
- Extraire State vers src/langgraph/state.py.
- Extraire modeles vers src/langgraph/schemas.py.
- Adapter imports dans src/langgraph/app.py.

### Etape 2
- Extraire format_response, normalize_text, to_chat_line, to_llm_message vers src/langgraph/message_utils.py.
- Garder signatures inchangees.

### Etape 3
- Extraire noeuds simples:
	- src/langgraph/nodes/chat.py
	- src/langgraph/nodes/code.py
	- src/langgraph/nodes/chikichiki.py

### Etape 4
- Extraire group_intent et classify_intent.
- Preserver le comportement actuel de request_reply.

### Etape 5
- Extraire RAG et handover.
- Verifier le flux: reply admin -> envoi Telegram -> persistance historique thread cible (aupdate_state).

### Etape 6
- Introduire src/langgraph/graph_builder.py.
- Reduire src/langgraph/app.py a orchestration minimale.

## Verifications a chaque etape
- Lancer tests existants.
- Verifier que les transitions du graphe n'ont pas change.
- Verifier les logs de group_intent et classify_intent.
- Verifier le cas request_reply:
	- message envoye au chat cible
	- historique ajoute dans le thread cible
	- pas de regression cote thread admin

## Risques connus
- Regressions de format message (JSON assistant/user).
- Perte de contexte si thread_id est mal construit.
- Couplage cache entre noeuds et utilitaires.

## Critere de fin
- src/langgraph/app.py < 150 lignes environ.
- Noeuds testables individuellement.
- Aucun changement de comportement observable cote bot.
