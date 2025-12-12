from typing import Dict, Any, Optional
from datetime import datetime
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import re

class QueryIntent(BaseModel):
    """Represents the intent extracted from a natural language query."""
    intent: str = Field(..., description="The type of query (count, sum, average, etc.)")
    metric: str = Field(..., description="The metric being queried (views, likes, comments, reports)")
    time_range: Optional[Dict[str, str]] = Field(None, description="Time range for the query")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Additional filters for the query")
    group_by: Optional[str] = Field(None, description="Field to group results by")

class NLPService:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(
            temperature=0,
            model_name="gpt-3.5-turbo",
            openai_api_key=openai_api_key
        )
        
        self.parser = PydanticOutputParser(pydantic_object=QueryIntent)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are a helpful assistant that translates natural language questions about video analytics into structured queries.
            The database has the following tables:
            
            Table: videos
            - id: integer (primary key)
            - creator_id: integer
            - video_created_at: datetime
            - views_count: integer
            - likes_count: integer
            - comments_count: integer
            - reports_count: integer
            - created_at: datetime
            - updated_at: datetime
            
            Table: video_snapshots
            - id: integer (primary key)
            - video_id: integer (foreign key to videos.id)
            - views_count: integer
            - likes_count: integer
            - comments_count: integer
            - reports_count: integer
            - delta_views_count: integer
            - delta_likes_count: integer
            - delta_comments_count: integer
            - delta_reports_count: integer
            - created_at: datetime
            - updated_at: datetime
            
            When analyzing a question:
            1. Determine if it's asking about videos or snapshots
            2. Identify the metric being queried (views, likes, comments, reports)
            3. Extract any time ranges or filters
            4. Determine if it's a count, sum, or other aggregation
            5. Identify any grouping
            
            Example questions and their interpretations:
            - "Сколько всего видео есть в системе?" -> count all videos
            - "Сколько видео у креатора с id 123 вышло с 1 ноября 2025 по 5 ноября 2025 включительно?" -> count videos by creator_id=123 between dates
            - "Сколько видео набрало больше 100000 просмотров за всё время?" -> count videos where views_count > 100000
            - "На сколько просмотров в сумме выросли все видео 28 ноября 2025?" -> sum of delta_views_count for snapshots on that date
            - "Сколько разных видео получали новые просмотры 27 ноября 2025?" -> count distinct video_ids from snapshots where created_at is that date and delta_views_count > 0
            
            Current date: {current_date}
            
            {format_instructions}
            
            Question: {question}
            """),
            ("human", "{question}")
        ])
        
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            output_parser=self.parser
        )
    
    def parse_query(self, question: str) -> QueryIntent:
        """Parse a natural language question into a structured query."""
        try:
            response = self.chain.run(
                question=question,
                current_date=datetime.now().strftime("%Y-%m-%d"),
                format_instructions=self.parser.get_format_instructions()
            )
            return response
        except Exception as e:
            print(f"Error parsing query: {e}")
            raise ValueError("Не удалось обработать ваш запрос. Пожалуйста, сформулируйте его иначе.")

class QueryBuilder:
    """Builds SQL queries from structured query intents."""
    
    @staticmethod
    def build_query(intent: QueryIntent) -> tuple[str, dict]:
        """Build a SQL query from a query intent."""
        if intent.intent == "count":
            return QueryBuilder._build_count_query(intent)
        elif intent.intent == "sum":
            return QueryBuilder._build_sum_query(intent)
        # Add more query types as needed
        else:
            raise ValueError(f"Unsupported query type: {intent.intent}")
    
    @staticmethod
    def _build_count_query(intent: QueryIntent) -> tuple[str, dict]:
        """Build a count query."""
        params = {}
        where_clauses = []
        
        # Handle time range
        if intent.time_range:
            if 'start' in intent.time_range:
                where_clauses.append("created_at >= :start_date")
                params['start_date'] = intent.time_range['start']
            if 'end' in intent.time_range:
                where_clauses.append("created_at <= :end_date")
                params['end_date'] = intent.time_range['end']
        
        # Handle filters
        for key, value in intent.filters.items():
            where_clauses.append(f"{key} = :{key}")
            params[key] = value
        
        # Build the query
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        if intent.metric == 'videos':
            query = f"SELECT COUNT(*) FROM videos {where_clause}"
        else:
            # For other metrics, we're likely querying snapshots
            query = f"SELECT COUNT(DISTINCT video_id) FROM video_snapshots {where_clause}"
        
        return query, params
    
    @staticmethod
    def _build_sum_query(intent: QueryIntent) -> tuple[str, dict]:
        """Build a sum query."""
        params = {}
        where_clauses = []
        
        # Handle time range
        if intent.time_range:
            if 'start' in intent.time_range:
                where_clauses.append("created_at >= :start_date")
                params['start_date'] = intent.time_range['start']
            if 'end' in intent.time_range:
                where_clauses.append("created_at <= :end_date")
                params['end_date'] = intent.time_range['end']
        
        # Handle filters
        for key, value in intent.filters.items():
            where_clauses.append(f"{key} = :{key}")
            params[key] = value
        
        # Determine the column to sum based on the metric
        metric_column = {
            'views': 'delta_views_count',
            'likes': 'delta_likes_count',
            'comments': 'delta_comments_count',
            'reports': 'delta_reports_count'
        }.get(intent.metric, 'delta_views_count')
        
        # Build the query
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"SELECT COALESCE(SUM({metric_column}), 0) FROM video_snapshots {where_clause}"
        
        return query, params
