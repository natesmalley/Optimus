/**
 * ResourceChart - Interactive chart component for resource usage visualization
 * Uses Recharts for responsive, animated charts
 */

import React from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { format } from 'date-fns';

interface ResourceChartProps {
  data: Array<{
    timestamp: Date;
    cpu: number;
    memory: number;
    storage: number;
    network: number;
  }>;
  selectedResource: 'cpu' | 'memory' | 'storage' | 'network';
  timeRange: '1h' | '6h' | '24h' | '7d';
  chartType?: 'line' | 'area';
}

export function ResourceChart({ 
  data, 
  selectedResource, 
  timeRange,
  chartType = 'area' 
}: ResourceChartProps) {
  // Format data for chart
  const chartData = data.map(point => ({
    timestamp: point.timestamp.getTime(),
    time: point.timestamp,
    cpu: Math.round(point.cpu * 100) / 100,
    memory: Math.round(point.memory * 100) / 100,
    storage: Math.round(point.storage * 100) / 100,
    network: Math.round(point.network * 100) / 100,
  }));

  const getTimeFormat = () => {
    switch (timeRange) {
      case '1h':
      case '6h':
        return 'HH:mm';
      case '24h':
        return 'HH:mm';
      case '7d':
        return 'MM/dd';
      default:
        return 'HH:mm';
    }
  };

  const formatXAxisLabel = (timestamp: number) => {
    return format(new Date(timestamp), getTimeFormat());
  };

  const formatTooltipLabel = (timestamp: number) => {
    return format(new Date(timestamp), 'MMM dd, HH:mm:ss');
  };

  const getResourceConfig = (resource: string) => {
    switch (resource) {
      case 'cpu':
        return {
          color: '#3B82F6',
          name: 'CPU Usage (%)',
          unit: '%',
          max: 100,
        };
      case 'memory':
        return {
          color: '#8B5CF6',
          name: 'Memory Usage (%)',
          unit: '%',
          max: 100,
        };
      case 'storage':
        return {
          color: '#10B981',
          name: 'Storage Usage (%)',
          unit: '%',
          max: 100,
        };
      case 'network':
        return {
          color: '#F59E0B',
          name: 'Network Usage (MB/s)',
          unit: ' MB/s',
          max: 100,
        };
      default:
        return {
          color: '#6B7280',
          name: 'Usage',
          unit: '',
          max: 100,
        };
    }
  };

  const config = getResourceConfig(selectedResource);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      return (
        <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
          <p className="text-sm text-gray-600 mb-1">
            {formatTooltipLabel(label)}
          </p>
          <p className="text-sm font-medium" style={{ color: config.color }}>
            {config.name}: {data.value.toFixed(1)}{config.unit}
          </p>
        </div>
      );
    }
    return null;
  };

  const getTickCount = () => {
    switch (timeRange) {
      case '1h': return 6;
      case '6h': return 6;
      case '24h': return 8;
      case '7d': return 7;
      default: return 6;
    }
  };

  if (chartType === 'area') {
    return (
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis
              dataKey="timestamp"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              tickFormatter={formatXAxisLabel}
              tickCount={getTickCount()}
              stroke="#6B7280"
              fontSize={12}
            />
            <YAxis
              domain={[0, config.max]}
              tickFormatter={(value) => `${value}${config.unit}`}
              stroke="#6B7280"
              fontSize={12}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey={selectedResource}
              stroke={config.color}
              fill={config.color}
              fillOpacity={0.1}
              strokeWidth={2}
              dot={false}
              activeDot={{
                r: 4,
                stroke: config.color,
                strokeWidth: 2,
                fill: '#FFFFFF',
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="timestamp"
            type="number"
            scale="time"
            domain={['dataMin', 'dataMax']}
            tickFormatter={formatXAxisLabel}
            tickCount={getTickCount()}
            stroke="#6B7280"
            fontSize={12}
          />
          <YAxis
            domain={[0, config.max]}
            tickFormatter={(value) => `${value}${config.unit}`}
            stroke="#6B7280"
            fontSize={12}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey={selectedResource}
            stroke={config.color}
            strokeWidth={2}
            dot={false}
            activeDot={{
              r: 4,
              stroke: config.color,
              strokeWidth: 2,
              fill: '#FFFFFF',
            }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// Multi-resource chart component
interface MultiResourceChartProps {
  data: Array<{
    timestamp: Date;
    cpu: number;
    memory: number;
    storage: number;
    network: number;
  }>;
  timeRange: '1h' | '6h' | '24h' | '7d';
  resources?: Array<'cpu' | 'memory' | 'storage' | 'network'>;
}

export function MultiResourceChart({ 
  data, 
  timeRange, 
  resources = ['cpu', 'memory'] 
}: MultiResourceChartProps) {
  const chartData = data.map(point => ({
    timestamp: point.timestamp.getTime(),
    time: point.timestamp,
    cpu: Math.round(point.cpu * 100) / 100,
    memory: Math.round(point.memory * 100) / 100,
    storage: Math.round(point.storage * 100) / 100,
    network: Math.round(point.network * 100) / 100,
  }));

  const getTimeFormat = () => {
    switch (timeRange) {
      case '1h':
      case '6h':
        return 'HH:mm';
      case '24h':
        return 'HH:mm';
      case '7d':
        return 'MM/dd';
      default:
        return 'HH:mm';
    }
  };

  const formatXAxisLabel = (timestamp: number) => {
    return format(new Date(timestamp), getTimeFormat());
  };

  const formatTooltipLabel = (timestamp: number) => {
    return format(new Date(timestamp), 'MMM dd, HH:mm:ss');
  };

  const resourceConfigs = {
    cpu: { color: '#3B82F6', name: 'CPU' },
    memory: { color: '#8B5CF6', name: 'Memory' },
    storage: { color: '#10B981', name: 'Storage' },
    network: { color: '#F59E0B', name: 'Network' },
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
          <p className="text-sm text-gray-600 mb-2">
            {formatTooltipLabel(label)}
          </p>
          {payload.map((entry: any, index: number) => (
            <p
              key={index}
              className="text-sm font-medium"
              style={{ color: entry.color }}
            >
              {entry.name}: {entry.value.toFixed(1)}%
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const getTickCount = () => {
    switch (timeRange) {
      case '1h': return 6;
      case '6h': return 6;
      case '24h': return 8;
      case '7d': return 7;
      default: return 6;
    }
  };

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="timestamp"
            type="number"
            scale="time"
            domain={['dataMin', 'dataMax']}
            tickFormatter={formatXAxisLabel}
            tickCount={getTickCount()}
            stroke="#6B7280"
            fontSize={12}
          />
          <YAxis
            domain={[0, 100]}
            tickFormatter={(value) => `${value}%`}
            stroke="#6B7280"
            fontSize={12}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          {resources.map(resource => (
            <Line
              key={resource}
              type="monotone"
              dataKey={resource}
              stroke={resourceConfigs[resource].color}
              name={resourceConfigs[resource].name}
              strokeWidth={2}
              dot={false}
              activeDot={{
                r: 3,
                stroke: resourceConfigs[resource].color,
                strokeWidth: 2,
                fill: '#FFFFFF',
              }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}