"""
Response Serialization Layer
Comprehensive response formatting, data transformation, and output optimization.
"""

import json
import xml.etree.ElementTree as ET
import csv
from typing import Dict, Any, List, Optional, Union, Type
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from io import StringIO
from dataclasses import asdict, is_dataclass

from pydantic import BaseModel
from fastapi import Request
from fastapi.responses import JSONResponse, Response

from ...config import logger


class ResponseFormat(str, Enum):
    """Response format types."""
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    TSV = "tsv"
    YAML = "yaml"


class SerializationError(Exception):
    """Custom serialization error."""
    
    def __init__(self, message: str, format_type: str = None, data_type: str = None):
        super().__init__(message)
        self.format_type = format_type
        self.data_type = data_type


class BaseSerializer:
    """Base serializer class with common serialization methods."""
    
    def __init__(self):
        self.datetime_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        self.date_format = "%Y-%m-%d"
        self.decimal_precision = 2
    
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format."""
        if dt is None:
            return None
        return dt.strftime(self.datetime_format)
    
    def serialize_date(self, d: date) -> str:
        """Serialize date to ISO format."""
        if d is None:
            return None
        return d.strftime(self.date_format)
    
    def serialize_decimal(self, value: Decimal) -> float:
        """Serialize decimal to float with precision."""
        if value is None:
            return None
        return round(float(value), self.decimal_precision)
    
    def clean_data(self, data: Any) -> Any:
        """Clean and prepare data for serialization."""
        if data is None:
            return None
        
        if isinstance(data, dict):
            return {key: self.clean_data(value) for key, value in data.items()}
        
        if isinstance(data, (list, tuple)):
            return [self.clean_data(item) for item in data]
        
        if isinstance(data, datetime):
            return self.serialize_datetime(data)
        
        if isinstance(data, date):
            return self.serialize_date(data)
        
        if isinstance(data, Decimal):
            return self.serialize_decimal(data)
        
        if isinstance(data, Enum):
            return data.value
        
        if is_dataclass(data):
            return self.clean_data(asdict(data))
        
        if isinstance(data, BaseModel):
            return self.clean_data(data.dict())
        
        if hasattr(data, '__dict__'):
            return self.clean_data(data.__dict__)
        
        return data
    
    def filter_fields(self, data: Dict[str, Any], include_fields: List[str] = None,
                     exclude_fields: List[str] = None) -> Dict[str, Any]:
        """Filter fields in response data."""
        if include_fields:
            data = {key: value for key, value in data.items() if key in include_fields}
        
        if exclude_fields:
            data = {key: value for key, value in data.items() if key not in exclude_fields}
        
        return data
    
    def transform_keys(self, data: Dict[str, Any], transform_func: callable) -> Dict[str, Any]:
        """Transform dictionary keys using provided function."""
        if not isinstance(data, dict):
            return data
        
        transformed = {}
        for key, value in data.items():
            new_key = transform_func(key)
            if isinstance(value, dict):
                transformed[new_key] = self.transform_keys(value, transform_func)
            elif isinstance(value, list):
                transformed[new_key] = [
                    self.transform_keys(item, transform_func) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                transformed[new_key] = value
        
        return transformed
    
    def snake_to_camel(self, snake_str: str) -> str:
        """Convert snake_case to camelCase."""
        components = snake_str.split('_')
        return components[0] + ''.join(x.capitalize() for x in components[1:])
    
    def camel_to_snake(self, camel_str: str) -> str:
        """Convert camelCase to snake_case."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class JSONSerializer(BaseSerializer):
    """JSON response serializer."""
    
    def serialize(self, data: Any, **kwargs) -> str:
        """Serialize data to JSON."""
        try:
            cleaned_data = self.clean_data(data)
            
            # Handle special options
            indent = kwargs.get('indent', None)
            sort_keys = kwargs.get('sort_keys', False)
            ensure_ascii = kwargs.get('ensure_ascii', False)
            
            return json.dumps(
                cleaned_data,
                indent=indent,
                sort_keys=sort_keys,
                ensure_ascii=ensure_ascii,
                default=str
            )
        except Exception as e:
            raise SerializationError(f"JSON serialization failed: {e}", "json")
    
    def serialize_response(self, data: Any, status_code: int = 200, 
                         headers: Dict[str, str] = None, **kwargs) -> JSONResponse:
        """Create JSON response."""
        try:
            cleaned_data = self.clean_data(data)
            
            response_headers = headers or {}
            response_headers["Content-Type"] = "application/json"
            
            return JSONResponse(
                content=cleaned_data,
                status_code=status_code,
                headers=response_headers
            )
        except Exception as e:
            raise SerializationError(f"JSON response creation failed: {e}", "json")


class XMLSerializer(BaseSerializer):
    """XML response serializer."""
    
    def serialize(self, data: Any, root_element: str = "response", **kwargs) -> str:
        """Serialize data to XML."""
        try:
            cleaned_data = self.clean_data(data)
            root = ET.Element(root_element)
            self._dict_to_xml(cleaned_data, root)
            
            return ET.tostring(root, encoding='unicode')
        except Exception as e:
            raise SerializationError(f"XML serialization failed: {e}", "xml")
    
    def _dict_to_xml(self, data: Any, parent: ET.Element):
        """Convert dictionary to XML elements."""
        if isinstance(data, dict):
            for key, value in data.items():
                # Ensure valid XML tag names
                safe_key = self._make_valid_xml_tag(key)
                child = ET.SubElement(parent, safe_key)
                
                if isinstance(value, (dict, list)):
                    self._dict_to_xml(value, child)
                else:
                    child.text = str(value) if value is not None else ""
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                child = ET.SubElement(parent, f"item_{i}")
                self._dict_to_xml(item, child)
        
        else:
            parent.text = str(data) if data is not None else ""
    
    def _make_valid_xml_tag(self, name: str) -> str:
        """Make a valid XML tag name."""
        import re
        # Replace invalid characters with underscores
        name = re.sub(r'[^a-zA-Z0-9_-]', '_', str(name))
        # Ensure it starts with a letter
        if name and not name[0].isalpha():
            name = f"tag_{name}"
        return name or "element"
    
    def serialize_response(self, data: Any, status_code: int = 200,
                         headers: Dict[str, str] = None, **kwargs) -> Response:
        """Create XML response."""
        try:
            xml_content = self.serialize(data, **kwargs)
            
            response_headers = headers or {}
            response_headers["Content-Type"] = "application/xml"
            
            return Response(
                content=xml_content,
                status_code=status_code,
                headers=response_headers,
                media_type="application/xml"
            )
        except Exception as e:
            raise SerializationError(f"XML response creation failed: {e}", "xml")


class CSVSerializer(BaseSerializer):
    """CSV response serializer."""
    
    def serialize(self, data: Any, **kwargs) -> str:
        """Serialize data to CSV."""
        try:
            cleaned_data = self.clean_data(data)
            
            if not isinstance(cleaned_data, list):
                raise SerializationError("CSV serialization requires list of dictionaries", "csv")
            
            if not cleaned_data:
                return ""
            
            # Get fieldnames from first item
            if isinstance(cleaned_data[0], dict):
                fieldnames = list(cleaned_data[0].keys())
            else:
                raise SerializationError("CSV serialization requires list of dictionaries", "csv")
            
            # Write CSV
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            
            if kwargs.get('include_header', True):
                writer.writeheader()
            
            for row in cleaned_data:
                if isinstance(row, dict):
                    writer.writerow(row)
            
            return output.getvalue()
        except Exception as e:
            raise SerializationError(f"CSV serialization failed: {e}", "csv")
    
    def serialize_response(self, data: Any, status_code: int = 200,
                         headers: Dict[str, str] = None, filename: str = None, **kwargs) -> Response:
        """Create CSV response."""
        try:
            csv_content = self.serialize(data, **kwargs)
            
            response_headers = headers or {}
            response_headers["Content-Type"] = "text/csv"
            
            if filename:
                response_headers["Content-Disposition"] = f'attachment; filename="{filename}"'
            
            return Response(
                content=csv_content,
                status_code=status_code,
                headers=response_headers,
                media_type="text/csv"
            )
        except Exception as e:
            raise SerializationError(f"CSV response creation failed: {e}", "csv")


class YAMLSerializer(BaseSerializer):
    """YAML response serializer."""
    
    def serialize(self, data: Any, **kwargs) -> str:
        """Serialize data to YAML."""
        try:
            import yaml
            cleaned_data = self.clean_data(data)
            
            return yaml.dump(
                cleaned_data,
                default_flow_style=kwargs.get('flow_style', False),
                default_style=kwargs.get('style', None),
                indent=kwargs.get('indent', 2)
            )
        except ImportError:
            raise SerializationError("PyYAML not installed", "yaml")
        except Exception as e:
            raise SerializationError(f"YAML serialization failed: {e}", "yaml")
    
    def serialize_response(self, data: Any, status_code: int = 200,
                         headers: Dict[str, str] = None, **kwargs) -> Response:
        """Create YAML response."""
        try:
            yaml_content = self.serialize(data, **kwargs)
            
            response_headers = headers or {}
            response_headers["Content-Type"] = "application/x-yaml"
            
            return Response(
                content=yaml_content,
                status_code=status_code,
                headers=response_headers,
                media_type="application/x-yaml"
            )
        except Exception as e:
            raise SerializationError(f"YAML response creation failed: {e}", "yaml")


class ResponseSerializer:
    """Main response serializer with format detection."""
    
    def __init__(self):
        self.serializers = {
            ResponseFormat.JSON: JSONSerializer(),
            ResponseFormat.XML: XMLSerializer(),
            ResponseFormat.CSV: CSVSerializer(),
            ResponseFormat.YAML: YAMLSerializer()
        }
    
    def detect_format(self, request: Request) -> ResponseFormat:
        """Detect desired response format from request."""
        # Check query parameter
        format_param = request.query_params.get('format', '').lower()
        if format_param in [f.value for f in ResponseFormat]:
            return ResponseFormat(format_param)
        
        # Check Accept header
        accept_header = request.headers.get('accept', '').lower()
        
        if 'application/json' in accept_header or 'application/vnd.api+json' in accept_header:
            return ResponseFormat.JSON
        elif 'application/xml' in accept_header or 'text/xml' in accept_header:
            return ResponseFormat.XML
        elif 'text/csv' in accept_header:
            return ResponseFormat.CSV
        elif 'application/x-yaml' in accept_header or 'text/yaml' in accept_header:
            return ResponseFormat.YAML
        
        # Default to JSON
        return ResponseFormat.JSON
    
    def serialize(self, data: Any, format_type: ResponseFormat = ResponseFormat.JSON, 
                 **kwargs) -> Union[str, Response]:
        """Serialize data in specified format."""
        if format_type not in self.serializers:
            raise SerializationError(f"Unsupported format: {format_type}")
        
        serializer = self.serializers[format_type]
        return serializer.serialize(data, **kwargs)
    
    def create_response(self, data: Any, request: Request = None,
                       format_type: ResponseFormat = None, status_code: int = 200,
                       headers: Dict[str, str] = None, **kwargs) -> Response:
        """Create response in appropriate format."""
        if format_type is None and request:
            format_type = self.detect_format(request)
        elif format_type is None:
            format_type = ResponseFormat.JSON
        
        if format_type not in self.serializers:
            raise SerializationError(f"Unsupported format: {format_type}")
        
        serializer = self.serializers[format_type]
        return serializer.serialize_response(data, status_code, headers, **kwargs)


# Response model classes
class SuccessResponse(BaseModel):
    """Standard success response."""
    success: bool = True
    data: Any = None
    message: Optional[str] = None
    timestamp: datetime = None
    request_id: Optional[str] = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        super().__init__(**data)


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    request_id: Optional[str] = None
    help_url: Optional[str] = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        super().__init__(**data)


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    data: List[Any]
    pagination: Dict[str, Any]
    total_count: int
    page: int
    size: int
    total_pages: int
    has_next: bool
    has_previous: bool


# Specific serialization functions
def serialize_project_response(project_data: Dict[str, Any], 
                             include_fields: List[str] = None,
                             exclude_fields: List[str] = None) -> Dict[str, Any]:
    """Serialize project response data."""
    serializer = BaseSerializer()
    
    # Clean and filter data
    cleaned_data = serializer.clean_data(project_data)
    filtered_data = serializer.filter_fields(cleaned_data, include_fields, exclude_fields)
    
    # Add metadata
    filtered_data['_metadata'] = {
        'serialized_at': datetime.now().isoformat(),
        'version': '1.0',
        'type': 'project'
    }
    
    return filtered_data


def serialize_council_response(council_data: Dict[str, Any],
                             include_persona_details: bool = True) -> Dict[str, Any]:
    """Serialize council deliberation response."""
    serializer = BaseSerializer()
    cleaned_data = serializer.clean_data(council_data)
    
    # Add council-specific metadata
    if not include_persona_details and 'persona_responses' in cleaned_data:
        # Summarize persona responses
        persona_summary = {
            'total_personas': len(cleaned_data['persona_responses']),
            'consensus_reached': cleaned_data.get('consensus_reached', False),
            'confidence_level': cleaned_data.get('confidence_level', 0.0)
        }
        cleaned_data['persona_summary'] = persona_summary
        del cleaned_data['persona_responses']
    
    cleaned_data['_metadata'] = {
        'serialized_at': datetime.now().isoformat(),
        'version': '1.0',
        'type': 'council_deliberation'
    }
    
    return cleaned_data


def serialize_orchestration_response(orchestration_data: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize orchestration response."""
    serializer = BaseSerializer()
    cleaned_data = serializer.clean_data(orchestration_data)
    
    # Add orchestration metadata
    cleaned_data['_metadata'] = {
        'serialized_at': datetime.now().isoformat(),
        'version': '1.0',
        'type': 'orchestration'
    }
    
    return cleaned_data


def serialize_deployment_response(deployment_data: Dict[str, Any],
                                include_logs: bool = False) -> Dict[str, Any]:
    """Serialize deployment response."""
    serializer = BaseSerializer()
    cleaned_data = serializer.clean_data(deployment_data)
    
    # Handle logs
    if not include_logs and 'logs' in cleaned_data:
        log_summary = {
            'total_logs': len(cleaned_data['logs']),
            'last_log_time': cleaned_data['logs'][-1].get('timestamp') if cleaned_data['logs'] else None
        }
        cleaned_data['log_summary'] = log_summary
        del cleaned_data['logs']
    
    cleaned_data['_metadata'] = {
        'serialized_at': datetime.now().isoformat(),
        'version': '1.0', 
        'type': 'deployment'
    }
    
    return cleaned_data


def serialize_error_response(error: Exception, request_id: str = None,
                           include_traceback: bool = False) -> Dict[str, Any]:
    """Serialize error response."""
    error_data = {
        'error': str(error),
        'error_type': type(error).__name__,
        'timestamp': datetime.now().isoformat(),
        'request_id': request_id
    }
    
    if hasattr(error, 'code'):
        error_data['error_code'] = error.code
    
    if hasattr(error, 'details'):
        error_data['details'] = error.details
    
    if include_traceback:
        import traceback
        error_data['traceback'] = traceback.format_exc()
    
    return error_data


# Global serializer instance
response_serializer = ResponseSerializer()


# Convenience functions
def create_success_response(data: Any, message: str = None, request_id: str = None) -> SuccessResponse:
    """Create standardized success response."""
    return SuccessResponse(
        data=data,
        message=message,
        request_id=request_id
    )


def create_error_response(error: str, error_code: str = None, details: Dict[str, Any] = None,
                         request_id: str = None, help_url: str = None) -> ErrorResponse:
    """Create standardized error response."""
    return ErrorResponse(
        error=error,
        error_code=error_code,
        details=details,
        request_id=request_id,
        help_url=help_url
    )


def serialize_response(data: Any, request: Request, **kwargs) -> Response:
    """Serialize response using global serializer."""
    return response_serializer.create_response(data, request, **kwargs)