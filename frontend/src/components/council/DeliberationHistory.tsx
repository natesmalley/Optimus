/**
 * Deliberation History Component
 * Displays recent deliberations in a compact format
 */

import React from 'react';
import type { DeliberationHistory as HistoryType, DeliberationResponse } from '@/types';

interface DeliberationHistoryProps {
  history: HistoryType;
  onSelectDeliberation?: (deliberation: DeliberationResponse) => void;
}

export function DeliberationHistory({ history, onSelectDeliberation }: DeliberationHistoryProps) {
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const formatTimeAgo = (timestamp: string) => {
    const now = new Date();
    const past = new Date(timestamp);
    const diffMs = now.getTime() - past.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  const truncateText = (text: string, maxLength: number) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  const handleDeliberationClick = (deliberation: any) => {
    if (onSelectDeliberation) {
      // Convert history item to full DeliberationResponse format
      const fullDeliberation: DeliberationResponse = {
        id: `historic_${Date.now()}`,
        query: deliberation.query,
        decision: deliberation.decision,
        confidence: deliberation.confidence,
        agreement_level: deliberation.agreement,
        deliberation_time: deliberation.time_taken,
        personas_consulted: deliberation.personas_consulted,
        timestamp: deliberation.timestamp,
        consensus_details: deliberation.consensus_details,
        supporting_personas: deliberation.consensus_details?.supporting_personas || [],
        dissenting_personas: deliberation.consensus_details?.dissenting_personas || [],
        alternative_views: deliberation.consensus_details?.alternative_views || {},
        statistics: deliberation.statistics || {},
      };
      onSelectDeliberation(fullDeliberation);
    }
  };

  if (!history.deliberations || history.deliberations.length === 0) {
    return (
      <div className="text-center py-6 text-gray-500">
        <p className="text-sm">No deliberations found.</p>
        <p className="text-xs mt-1">Submit a query to get started!</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {history.deliberations.map((deliberation, index) => (
        <div
          key={`${deliberation.timestamp}-${index}`}
          className={`border border-gray-200 rounded-lg p-3 transition-colors hover:bg-gray-50 ${
            onSelectDeliberation ? 'cursor-pointer' : ''
          }`}
          onClick={() => handleDeliberationClick(deliberation)}
        >
          {/* Header */}
          <div className="flex items-start justify-between mb-2">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {truncateText(deliberation.query, 80)}
              </p>
              <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                <span>{formatTimeAgo(deliberation.timestamp)}</span>
                <span>•</span>
                <span>{deliberation.personas_consulted} personas</span>
                <span>•</span>
                <span>{deliberation.time_taken.toFixed(1)}s</span>
              </div>
            </div>
            <div className={`text-xs font-medium ${getConfidenceColor(deliberation.confidence)}`}>
              {Math.round(deliberation.confidence * 100)}%
            </div>
          </div>

          {/* Decision Preview */}
          <div className="bg-gray-50 rounded p-2">
            <p className="text-xs text-gray-700">
              {truncateText(deliberation.decision, 120)}
            </p>
          </div>

          {/* Metrics Bar */}
          <div className="flex items-center justify-between mt-2 text-xs">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-gray-600">
                  {Math.round(deliberation.agreement * 100)}% agreement
                </span>
              </div>
            </div>
            {onSelectDeliberation && (
              <div className="text-blue-600 hover:text-blue-700">
                View Details →
              </div>
            )}
          </div>
        </div>
      ))}

      {/* Load More / Summary */}
      <div className="text-center pt-3 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          Showing {history.deliberations.length} of {history.total} deliberations
        </p>
        {history.total > history.deliberations.length && (
          <button className="text-xs text-blue-600 hover:text-blue-700 mt-1">
            Load more...
          </button>
        )}
      </div>
    </div>
  );
}