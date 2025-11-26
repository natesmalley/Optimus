/**
 * Utility functions for the dashboard
 */

import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format, formatDistanceToNow, parseISO } from 'date-fns';

/**
 * Combines class names using clsx and tailwind-merge
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Formats bytes to human-readable string
 */
export function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Formats percentage with optional decimals
 */
export function formatPercentage(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`;
}

/**
 * Formats large numbers with units (K, M, B, etc.)
 */
export function formatNumber(num: number, decimals = 1): string {
  if (num < 1000) return num.toString();

  const units = ['K', 'M', 'B', 'T'];
  let unitIndex = -1;
  let scaledNum = num;

  while (scaledNum >= 1000 && unitIndex < units.length - 1) {
    scaledNum /= 1000;
    unitIndex++;
  }

  return `${scaledNum.toFixed(decimals)}${units[unitIndex]}`;
}

/**
 * Formats currency values
 */
export function formatCurrency(amount: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Formats ISO date string to relative time
 */
export function formatRelativeTime(isoString: string): string {
  try {
    return formatDistanceToNow(parseISO(isoString), { addSuffix: true });
  } catch {
    return 'Unknown';
  }
}

/**
 * Formats ISO date string to human-readable format
 */
export function formatDate(isoString: string, formatStr = 'PPp'): string {
  try {
    return format(parseISO(isoString), formatStr);
  } catch {
    return 'Invalid date';
  }
}

/**
 * Gets status color based on status string
 */
export function getStatusColor(status: string): string {
  const statusColors: Record<string, string> = {
    active: 'text-green-600 bg-green-100 border-green-200',
    running: 'text-green-600 bg-green-100 border-green-200',
    discovered: 'text-blue-600 bg-blue-100 border-blue-200',
    starting: 'text-yellow-600 bg-yellow-100 border-yellow-200',
    stopped: 'text-gray-600 bg-gray-100 border-gray-200',
    error: 'text-red-600 bg-red-100 border-red-200',
    archived: 'text-gray-600 bg-gray-100 border-gray-200',
  };

  return statusColors[status.toLowerCase()] || 'text-gray-600 bg-gray-100 border-gray-200';
}

/**
 * Gets grade color based on letter grade
 */
export function getGradeColor(grade: string): string {
  const gradeColors: Record<string, string> = {
    A: 'text-green-700 bg-green-100',
    B: 'text-blue-700 bg-blue-100',
    C: 'text-yellow-700 bg-yellow-100',
    D: 'text-orange-700 bg-orange-100',
    F: 'text-red-700 bg-red-100',
  };

  return gradeColors[grade] || 'text-gray-700 bg-gray-100';
}

/**
 * Gets health score color based on score value
 */
export function getHealthScoreColor(score: number): string {
  if (score >= 90) return 'text-green-600';
  if (score >= 80) return 'text-blue-600';
  if (score >= 70) return 'text-yellow-600';
  if (score >= 60) return 'text-orange-600';
  return 'text-red-600';
}

/**
 * Debounces function calls
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(null, args), delay);
  };
}

/**
 * Throttles function calls
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void {
  let lastCall = 0;
  
  return (...args: Parameters<T>) => {
    const now = Date.now();
    if (now - lastCall >= delay) {
      lastCall = now;
      func.apply(null, args);
    }
  };
}

/**
 * Generates random ID
 */
export function generateId(): string {
  return Math.random().toString(36).substring(2) + Date.now().toString(36);
}

/**
 * Capitalizes first letter of string
 */
export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Converts string to title case
 */
export function toTitleCase(str: string): string {
  return str.replace(/\w\S*/g, (txt) => 
    txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
  );
}

/**
 * Truncates text with ellipsis
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

/**
 * Gets technology icon name based on tech stack
 */
export function getTechIcon(tech: string): string {
  const techIcons: Record<string, string> = {
    javascript: 'javascript',
    typescript: 'typescript',
    python: 'python',
    java: 'coffee',
    react: 'react',
    vue: 'vue',
    angular: 'angular',
    node: 'nodejs',
    express: 'express',
    fastapi: 'fastapi',
    django: 'django',
    flask: 'flask',
    docker: 'docker',
    kubernetes: 'kubernetes',
    aws: 'aws',
    azure: 'microsoft-azure',
    gcp: 'google-cloud',
    mongodb: 'mongodb',
    postgresql: 'postgresql',
    mysql: 'mysql',
    redis: 'redis',
    git: 'git',
    github: 'github',
    gitlab: 'gitlab',
  };

  return techIcons[tech.toLowerCase()] || 'code';
}

/**
 * Calculates trend percentage change
 */
export function calculateTrendChange(current: number, previous: number): {
  percentage: number;
  direction: 'up' | 'down' | 'neutral';
} {
  if (previous === 0) {
    return { percentage: 0, direction: 'neutral' };
  }

  const percentage = ((current - previous) / previous) * 100;
  const direction = percentage > 0 ? 'up' : percentage < 0 ? 'down' : 'neutral';

  return { percentage: Math.abs(percentage), direction };
}

/**
 * Validates email format
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Deep clone object
 */
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') return obj;
  if (obj instanceof Date) return new Date(obj.getTime()) as unknown as T;
  if (obj instanceof Array) return obj.map(item => deepClone(item)) as unknown as T;
  if (typeof obj === 'object') {
    const clonedObj = {} as { [key: string]: any };
    for (const key in obj) {
      clonedObj[key] = deepClone(obj[key]);
    }
    return clonedObj as T;
  }
  return obj;
}