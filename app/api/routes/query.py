import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from app.core.config import settings
from app.models.schemas import QueryRequest, QueryResponse
from app.services.vector_store import load_index

router = APIRouter(prefix="/query", tags=["query"])

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Answer the question using only the context below.\n\nContext:\n{context}"),
    ("human", "{input}"),
])


def _format_docs(docs) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def _get_llm():
    if settings.use_huggingface:
        from langchain_huggingface import HuggingFaceEndpoint
        return HuggingFaceEndpoint(
            repo_id=settings.hf_model,
            huggingfacehub_api_token=settings.hf_api_token,
            temperature=0.1,
            max_new_tokens=512,
        )
    else:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )


def _build_chain(index_id: str, k: int):
    store = load_index(index_id)
    retriever = store.as_retriever(search_kwargs={"k": k})
    chain = (
        {"context": retriever | _format_docs, "input": RunnablePassthrough()}
        | _PROMPT
        | _get_llm()
        | StrOutputParser()
    )
    return chain, retriever


async def _stream_response(index_id: str, query: str, k: int) -> AsyncGenerator[str, None]:
    store = load_index(index_id)
    retriever = store.as_retriever(search_kwargs={"k": k})
    docs = retriever.invoke(query)

    sources = list({doc.metadata.get("source", "unknown") for doc in docs})
    context = _format_docs(docs)
    prompt_value = _PROMPT.invoke({"context": context, "input": query})

    yield f"data: sources={','.join(sources)}\n\n"
    async for chunk in _get_llm().astream(prompt_value):
        content = chunk.content if hasattr(chunk, "content") else str(chunk)
        yield f"data: {content}\n\n"
        await asyncio.sleep(0)
    yield "data: [DONE]\n\n"


@router.post("/", response_model=QueryResponse)
async def query_index(req: QueryRequest):
    k = req.k or settings.retrieval_k

    if req.stream:
        try:
            load_index(req.index_id)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        return StreamingResponse(
            _stream_response(req.index_id, req.query, k),
            media_type="text/event-stream",
        )

    try:
        chain, retriever = _build_chain(req.index_id, k)
        docs = retriever.invoke(req.query)
        answer = chain.invoke(req.query)
        sources = list({doc.metadata.get("source", "unknown") for doc in docs})
        return QueryResponse(answer=answer, sources=sources, index_id=req.index_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
