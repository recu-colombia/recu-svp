from app.application.services.antecedent_resolver import AntecedentResolver
from app.application.services.concatenation_engine import ConcatenationEngine
from app.application.services.rule_resolver import RuleResolver
from app.application.use_cases.analyze_auto_use_case import AnalyzeAutoUseCase
from app.infrastructure.ai.openai_router import OpenAILanguageModelRouter
from app.infrastructure.db.repositories import (
    PostgresActuacionRepository,
    PostgresCatalogRepository,
    PostgresRuleRepository,
)
from app.infrastructure.db.session import create_db_engine
from app.infrastructure.documents.pdf_extractor import PDFDocumentExtractor


def build_analyze_auto_use_case() -> AnalyzeAutoUseCase:
    engine = create_db_engine()
    rule_repository = PostgresRuleRepository(engine=engine)
    actuacion_repository = PostgresActuacionRepository(engine=engine)
    catalog_repository = PostgresCatalogRepository(engine=engine)

    return AnalyzeAutoUseCase(
        document_extractor=PDFDocumentExtractor(),
        language_model=OpenAILanguageModelRouter(),
        catalog_repository=catalog_repository,
        rule_resolver=RuleResolver(rule_repository),
        antecedent_resolver=AntecedentResolver(actuacion_repository),
        concatenation_engine=ConcatenationEngine(),
    )
