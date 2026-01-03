"""
Vector database service for Qdrant integration
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from qdrant_client.http import models
from app.utils.config import QDRANT_ENDPOINT, QDRANT_KEY, QDRANT_COLLECTION_NAME
from google import genai
from app.utils.config import GOOGLE_API_KEY
import logging
from typing import List, Dict, Optional
import uuid

logger = logging.getLogger(__name__)

class VectorDBService:
    """Service for managing vector embeddings in Qdrant"""
    
    def __init__(self):
        """Initialize Qdrant client and embedding model"""
        self.client = None
        self.collection_name = QDRANT_COLLECTION_NAME or "whatsapp_documents"
        self.genai_client = None
        
        # Initialize Qdrant client
        if QDRANT_ENDPOINT:
            try:
                if QDRANT_KEY:
                    self.client = QdrantClient(
                        url=QDRANT_ENDPOINT,
                        api_key=QDRANT_KEY
                    )
                    logger.info(f"Connected to Qdrant at {QDRANT_ENDPOINT} with API key")
                else:
                    self.client = QdrantClient(url=QDRANT_ENDPOINT)
                    logger.info(f"Connected to Qdrant at {QDRANT_ENDPOINT} (no API key)")
            except Exception as e:
                logger.error(f"Failed to connect to Qdrant: {e}")
                raise
        else:
            logger.warning("QDRANT_ENDPOINT not set. Vector database features will be disabled.")
        
        # Initialize Google Gemini client for embeddings
        if GOOGLE_API_KEY:
            try:
                self.genai_client = genai.Client(api_key=GOOGLE_API_KEY)
                logger.info("Initialized Google Gemini for embeddings")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                raise
        else:
            logger.warning("GOOGLE_API_KEY not set. Embeddings will not work.")
        
        # Create collection if it doesn't exist
        if self.client:
            self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """Create Qdrant collection if it doesn't exist"""
        if not self.client:
            return
        
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name not in collection_names:
                # Create collection with 768 dimensions (text-embedding-004 embedding size)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=768,  # text-embedding-004 dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using Google Gemini text-embedding-004
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        if not self.genai_client:
            raise ValueError("Gemini client not initialized")
        
        try:
            # Use text-embedding-004 model for embeddings
            # The API expects 'contents' (plural) as a list, not 'content' (singular)
            response = self.genai_client.models.embed_content(
                model="text-embedding-004",
                contents=[text]  # Use 'contents' (plural) as a list
            )
            
            # Extract embedding from response - handle different response formats
            embedding = None
            
            # Check if response has embedding attribute
            if hasattr(response, 'embedding'):
                embedding = response.embedding
            elif hasattr(response, 'values'):
                embedding = response.values
            elif hasattr(response, 'embeddings') and isinstance(response.embeddings, list) and len(response.embeddings) > 0:
                # If it's a list of embeddings, take the first one
                embedding = response.embeddings[0]
                if hasattr(embedding, 'values'):
                    embedding = embedding.values
            elif isinstance(response, dict):
                if 'embedding' in response:
                    embedding = response['embedding']
                elif 'values' in response:
                    embedding = response['values']
                elif 'embeddings' in response and isinstance(response['embeddings'], list) and len(response['embeddings']) > 0:
                    embedding = response['embeddings'][0]
            elif isinstance(response, list) and len(response) > 0:
                # If response is a list, take first element
                embedding = response[0]
                if isinstance(embedding, dict):
                    embedding = embedding.get('embedding') or embedding.get('values')
            
            if embedding is None:
                logger.error(f"Could not extract embedding from response. Response type: {type(response)}")
                logger.error(f"Response attributes: {dir(response) if hasattr(response, '__dict__') else 'N/A'}")
                raise ValueError("Could not extract embedding from response")
            
            # Ensure embedding is a list
            if not isinstance(embedding, list):
                embedding = list(embedding)
            
            logger.debug(f"Generated embedding of size {len(embedding)}")
            return embedding
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            raise
    
    def store_document_chunks(
        self,
        chunks: List[Dict[str, any]],
        user_phone: str,
        document_id: str,
        filename: str
    ) -> bool:
        """
        Store document chunks in Qdrant
        
        Args:
            chunks: List of chunk dictionaries with 'text' and 'metadata'
            user_phone: User's phone number
            document_id: Unique document identifier
            filename: Original filename
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.error("Qdrant client not initialized")
            return False
        
        try:
            points = []
            for idx, chunk in enumerate(chunks):
                # Generate embedding for chunk text
                embedding = self._get_embedding(chunk['text'])
                
                # Create point with embedding and metadata
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "text": chunk['text'],
                        "user_phone": user_phone,
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_index": idx,
                        "total_chunks": len(chunks)
                    }
                )
                points.append(point)
            
            # Upsert points to Qdrant in batches (Qdrant recommends batches of 100)
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
                logger.info(f"Stored batch {i//batch_size + 1} ({len(batch)} chunks)")
            
            logger.info(f"Successfully stored {len(points)} chunks for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing document chunks: {e}", exc_info=True)
            return False
    
    def search_relevant_chunks(
        self,
        query: str,
        user_phone: str,
        limit: int = 5
    ) -> List[Dict[str, any]]:
        """
        Search for relevant document chunks based on query
        
        Args:
            query: User's query text
            user_phone: User's phone number (to filter by user)
            limit: Maximum number of results
            
        Returns:
            List of relevant chunks with metadata
        """
        if not self.client:
            logger.warning("Qdrant client not initialized, returning empty results")
            return []
        
        try:
            # Generate embedding for query
            query_embedding = self._get_embedding(query)
            
            # Search in Qdrant with user filter
            # Check available methods and use the correct one
            if not hasattr(self.client, 'search'):
                # Check if it's an older version with different API
                available_methods = [m for m in dir(self.client) if 'search' in m.lower() or 'query' in m.lower()]
                logger.error(f"QdrantClient does not have 'search' method. Available search/query methods: {available_methods}")
                logger.error("Please upgrade qdrant-client: pip install --upgrade qdrant-client")
                raise AttributeError("QdrantClient.search() method not found. Please upgrade qdrant-client package.")
            
            # Use search method (standard in qdrant-client 1.0+)
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_phone",
                            match=MatchValue(value=user_phone)
                        )
                    ]
                ),
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            # Format results
            results = []
            for result in search_results:
                results.append({
                    "text": result.payload.get("text", ""),
                    "score": result.score,
                    "filename": result.payload.get("filename", ""),
                    "document_id": result.payload.get("document_id", ""),
                    "chunk_index": result.payload.get("chunk_index", 0)
                })
            
            logger.info(f"Found {len(results)} relevant chunks for query: '{query[:50]}...'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching chunks: {e}", exc_info=True)
            return []
    
    def delete_user_documents(self, user_phone: str) -> bool:
        """
        Delete all documents for a user
        
        Args:
            user_phone: User's phone number
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.error("Qdrant client not initialized")
            return False
        
        try:
            # Delete points matching user_phone
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="user_phone",
                                match=models.MatchValue(value=user_phone)
                            )
                        ]
                    )
                )
            )
            
            logger.info(f"Deleted all documents for user {user_phone}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user documents: {e}", exc_info=True)
            return False
    
    def is_configured(self) -> bool:
        """Check if vector database is properly configured"""
        return self.client is not None and self.genai_client is not None

