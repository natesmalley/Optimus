"""
Pagination Utilities
Comprehensive pagination support with cursor-based and offset-based pagination.
"""

import math
from typing import List, Dict, Any, Optional, Union, Tuple, TypeVar, Generic
from urllib.parse import urlencode

from pydantic import BaseModel, Field
from fastapi import Request, Query

T = TypeVar('T')


class PaginationType(str):
    """Pagination types."""
    OFFSET = "offset"  # Traditional page-based pagination
    CURSOR = "cursor"  # Cursor-based pagination for large datasets
    KEYSET = "keyset"  # Keyset pagination for consistent ordering


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(1, ge=1, description="Page number (1-based)")
    size: int = Field(20, ge=1, le=1000, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: str = Field("asc", regex="^(asc|desc)$", description="Sort order")
    cursor: Optional[str] = Field(None, description="Cursor for cursor-based pagination")
    
    @property
    def offset(self) -> int:
        """Calculate offset from page and size."""
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> int:
        """Get limit (same as size)."""
        return self.size


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    page: int
    size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_previous: bool
    next_page: Optional[int] = None
    previous_page: Optional[int] = None
    first_page: int = 1
    last_page: Optional[int] = None


class CursorMeta(BaseModel):
    """Cursor-based pagination metadata."""
    size: int
    has_next: bool
    has_previous: bool
    next_cursor: Optional[str] = None
    previous_cursor: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = "asc"


class PaginationLinks(BaseModel):
    """Pagination navigation links."""
    self: str
    first: Optional[str] = None
    last: Optional[str] = None
    next: Optional[str] = None
    previous: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    data: List[T]
    meta: Union[PaginationMeta, CursorMeta]
    links: Optional[PaginationLinks] = None
    
    class Config:
        arbitrary_types_allowed = True


class OffsetPaginator:
    """Offset-based paginator for traditional page navigation."""
    
    def __init__(self, total_count: int, params: PaginationParams):
        self.total_count = total_count
        self.params = params
        self.total_pages = math.ceil(total_count / params.size) if total_count > 0 else 0
    
    def get_meta(self) -> PaginationMeta:
        """Get pagination metadata."""
        has_next = self.params.page < self.total_pages
        has_previous = self.params.page > 1
        
        return PaginationMeta(
            page=self.params.page,
            size=self.params.size,
            total_count=self.total_count,
            total_pages=self.total_pages,
            has_next=has_next,
            has_previous=has_previous,
            next_page=self.params.page + 1 if has_next else None,
            previous_page=self.params.page - 1 if has_previous else None,
            first_page=1,
            last_page=self.total_pages if self.total_pages > 0 else None
        )
    
    def paginate(self, items: List[T]) -> PaginatedResponse[T]:
        """Paginate items."""
        # Apply offset and limit
        start_idx = self.params.offset
        end_idx = start_idx + self.params.size
        page_items = items[start_idx:end_idx]
        
        return PaginatedResponse(
            data=page_items,
            meta=self.get_meta()
        )
    
    def create_links(self, base_url: str, query_params: Dict[str, Any] = None) -> PaginationLinks:
        """Create pagination links."""
        query_params = query_params or {}
        meta = self.get_meta()
        
        links = PaginationLinks(self=self._build_url(base_url, self.params.page, query_params))
        
        if meta.has_previous:
            links.previous = self._build_url(base_url, meta.previous_page, query_params)
            links.first = self._build_url(base_url, 1, query_params)
        
        if meta.has_next:
            links.next = self._build_url(base_url, meta.next_page, query_params)
            links.last = self._build_url(base_url, meta.last_page, query_params)
        
        return links
    
    def _build_url(self, base_url: str, page: int, query_params: Dict[str, Any]) -> str:
        """Build URL with pagination parameters."""
        params = {
            **query_params,
            'page': page,
            'size': self.params.size
        }
        
        if self.params.sort_by:
            params['sort_by'] = self.params.sort_by
            params['sort_order'] = self.params.sort_order
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        query_string = urlencode(params)
        return f"{base_url}?{query_string}" if query_string else base_url


class CursorPaginator:
    """Cursor-based paginator for large datasets."""
    
    def __init__(self, params: PaginationParams, cursor_field: str = "id"):
        self.params = params
        self.cursor_field = cursor_field
    
    def encode_cursor(self, item: Dict[str, Any]) -> str:
        """Encode cursor from item."""
        import base64
        import json
        
        cursor_data = {
            "field": self.cursor_field,
            "value": item.get(self.cursor_field),
            "sort_order": self.params.sort_order
        }
        
        cursor_json = json.dumps(cursor_data, default=str)
        return base64.b64encode(cursor_json.encode()).decode()
    
    def decode_cursor(self, cursor: str) -> Dict[str, Any]:
        """Decode cursor to get position information."""
        import base64
        import json
        
        try:
            cursor_json = base64.b64decode(cursor.encode()).decode()
            return json.loads(cursor_json)
        except Exception:
            return {"field": self.cursor_field, "value": None, "sort_order": "asc"}
    
    def get_meta(self, items: List[Dict[str, Any]], has_more: bool = False) -> CursorMeta:
        """Get cursor pagination metadata."""
        next_cursor = None
        previous_cursor = None
        
        if items and has_more:
            next_cursor = self.encode_cursor(items[-1])
        
        if self.params.cursor:
            # For previous cursor, we'd need to implement reverse pagination logic
            # This is simplified for demo purposes
            previous_cursor = None
        
        return CursorMeta(
            size=self.params.size,
            has_next=has_more,
            has_previous=bool(self.params.cursor),
            next_cursor=next_cursor,
            previous_cursor=previous_cursor,
            sort_by=self.params.sort_by or self.cursor_field,
            sort_order=self.params.sort_order
        )
    
    def paginate(self, items: List[Dict[str, Any]], has_more: bool = False) -> PaginatedResponse[Dict[str, Any]]:
        """Paginate items with cursor."""
        return PaginatedResponse(
            data=items[:self.params.size],  # Limit to requested size
            meta=self.get_meta(items, has_more)
        )
    
    def create_links(self, base_url: str, items: List[Dict[str, Any]], 
                    has_more: bool = False, query_params: Dict[str, Any] = None) -> PaginationLinks:
        """Create cursor-based pagination links."""
        query_params = query_params or {}
        meta = self.get_meta(items, has_more)
        
        # Current link
        current_params = {**query_params, 'size': self.params.size}
        if self.params.cursor:
            current_params['cursor'] = self.params.cursor
        
        links = PaginationLinks(self=self._build_cursor_url(base_url, current_params))
        
        # Next link
        if meta.next_cursor:
            next_params = {**query_params, 'size': self.params.size, 'cursor': meta.next_cursor}
            links.next = self._build_cursor_url(base_url, next_params)
        
        # Previous link (simplified - would need proper implementation)
        if meta.previous_cursor:
            prev_params = {**query_params, 'size': self.params.size, 'cursor': meta.previous_cursor}
            links.previous = self._build_cursor_url(base_url, prev_params)
        
        return links
    
    def _build_cursor_url(self, base_url: str, params: Dict[str, Any]) -> str:
        """Build URL with cursor parameters."""
        if self.params.sort_by:
            params['sort_by'] = self.params.sort_by
            params['sort_order'] = self.params.sort_order
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        query_string = urlencode(params)
        return f"{base_url}?{query_string}" if query_string else base_url


class SearchPaginator(OffsetPaginator):
    """Paginator with search capabilities."""
    
    def __init__(self, total_count: int, params: PaginationParams, 
                 search_query: str = None, filters: Dict[str, Any] = None):
        super().__init__(total_count, params)
        self.search_query = search_query
        self.filters = filters or {}
    
    def create_links(self, base_url: str, query_params: Dict[str, Any] = None) -> PaginationLinks:
        """Create pagination links with search parameters."""
        query_params = query_params or {}
        
        # Add search parameters
        if self.search_query:
            query_params['q'] = self.search_query
        
        # Add filters
        query_params.update(self.filters)
        
        return super().create_links(base_url, query_params)


# Utility functions
def extract_pagination_params(
    page: int = Query(1, ge=1, le=10000, description="Page number"),
    size: int = Query(20, ge=1, le=1000, description="Page size"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    cursor: Optional[str] = Query(None, description="Cursor for pagination")
) -> PaginationParams:
    """Extract pagination parameters from query parameters."""
    return PaginationParams(
        page=page,
        size=size,
        sort_by=sort_by,
        sort_order=sort_order,
        cursor=cursor
    )


def paginate_results(
    items: List[T], 
    total_count: int, 
    params: PaginationParams,
    request: Request = None,
    pagination_type: str = PaginationType.OFFSET
) -> PaginatedResponse[T]:
    """Paginate results using specified pagination type."""
    
    if pagination_type == PaginationType.CURSOR:
        paginator = CursorPaginator(params)
        return paginator.paginate(items)
    else:
        paginator = OffsetPaginator(total_count, params)
        result = paginator.paginate(items)
        
        # Add links if request is provided
        if request:
            base_url = str(request.url).split('?')[0]
            query_params = dict(request.query_params)
            # Remove pagination params to avoid duplication
            query_params.pop('page', None)
            query_params.pop('size', None)
            query_params.pop('sort_by', None)
            query_params.pop('sort_order', None)
            
            result.links = paginator.create_links(base_url, query_params)
        
        return result


def create_pagination_links(
    base_url: str, 
    params: PaginationParams, 
    total_count: int,
    query_params: Dict[str, Any] = None
) -> PaginationLinks:
    """Create pagination links."""
    paginator = OffsetPaginator(total_count, params)
    return paginator.create_links(base_url, query_params)


def paginate_query_results(
    query_func: callable,
    count_func: callable, 
    params: PaginationParams,
    request: Request = None,
    filters: Dict[str, Any] = None
) -> PaginatedResponse:
    """Paginate database query results."""
    filters = filters or {}
    
    # Get total count
    total_count = count_func(filters) if filters else count_func()
    
    # Get paginated results
    offset = params.offset
    limit = params.limit
    
    # Apply sorting if specified
    sort_params = {}
    if params.sort_by:
        sort_params['sort_by'] = params.sort_by
        sort_params['sort_order'] = params.sort_order
    
    items = query_func(
        offset=offset,
        limit=limit,
        filters=filters,
        **sort_params
    )
    
    return paginate_results(items, total_count, params, request)


class AsyncPaginator:
    """Async paginator for database queries."""
    
    def __init__(self, params: PaginationParams):
        self.params = params
    
    async def paginate_async_query(
        self,
        query_func: callable,
        count_func: callable,
        request: Request = None,
        filters: Dict[str, Any] = None
    ) -> PaginatedResponse:
        """Paginate async database query results."""
        filters = filters or {}
        
        # Get total count
        total_count = await count_func(filters) if filters else await count_func()
        
        # Get paginated results
        offset = self.params.offset
        limit = self.params.limit
        
        # Apply sorting
        sort_params = {}
        if self.params.sort_by:
            sort_params['sort_by'] = self.params.sort_by
            sort_params['sort_order'] = self.params.sort_order
        
        items = await query_func(
            offset=offset,
            limit=limit,
            filters=filters,
            **sort_params
        )
        
        return paginate_results(items, total_count, self.params, request)


# Validation utilities
def validate_sort_field(sort_by: str, allowed_fields: List[str]) -> bool:
    """Validate sort field against allowed fields."""
    if not sort_by:
        return True
    
    # Handle nested field access (e.g., "user.name")
    base_field = sort_by.split('.')[0]
    return base_field in allowed_fields


def apply_sorting(items: List[Dict[str, Any]], sort_by: str = None, 
                 sort_order: str = "asc") -> List[Dict[str, Any]]:
    """Apply sorting to items list."""
    if not sort_by or not items:
        return items
    
    reverse = sort_order.lower() == "desc"
    
    try:
        # Handle nested field access
        if '.' in sort_by:
            def get_nested_value(item, path):
                value = item
                for key in path.split('.'):
                    value = value.get(key, '')
                    if value is None:
                        return ''
                return value
            
            return sorted(items, key=lambda x: get_nested_value(x, sort_by), reverse=reverse)
        else:
            return sorted(items, key=lambda x: x.get(sort_by, ''), reverse=reverse)
    
    except Exception:
        # Return original items if sorting fails
        return items


# Advanced pagination features
class FilteredPaginator(OffsetPaginator):
    """Paginator with advanced filtering capabilities."""
    
    def __init__(self, total_count: int, params: PaginationParams, 
                 filters: Dict[str, Any] = None, search_fields: List[str] = None):
        super().__init__(total_count, params)
        self.filters = filters or {}
        self.search_fields = search_fields or []
    
    def apply_filters(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply filters to items."""
        filtered_items = items
        
        for field, value in self.filters.items():
            if value is not None:
                filtered_items = [
                    item for item in filtered_items 
                    if self._matches_filter(item, field, value)
                ]
        
        return filtered_items
    
    def _matches_filter(self, item: Dict[str, Any], field: str, value: Any) -> bool:
        """Check if item matches filter criteria."""
        item_value = item.get(field)
        
        if isinstance(value, str) and isinstance(item_value, str):
            # Case-insensitive string matching
            return value.lower() in item_value.lower()
        
        if isinstance(value, list):
            # Check if item value is in the list
            return item_value in value
        
        return item_value == value
    
    def search(self, items: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Search items across specified fields."""
        if not query or not self.search_fields:
            return items
        
        query_lower = query.lower()
        return [
            item for item in items
            if any(
                query_lower in str(item.get(field, '')).lower()
                for field in self.search_fields
            )
        ]


# FastAPI dependency
def get_pagination_params(
    page: int = Query(1, ge=1, le=10000, description="Page number"),
    size: int = Query(20, ge=1, le=1000, description="Page size"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order")
) -> PaginationParams:
    """FastAPI dependency for pagination parameters."""
    return PaginationParams(
        page=page,
        size=size,
        sort_by=sort_by,
        sort_order=sort_order
    )