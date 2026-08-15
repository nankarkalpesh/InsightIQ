import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  BarChart3,
  Check,
  Info,
  LineChart as LineIcon,
  Loader2,
  PieChart as PieIcon,
  PlusCircle,
  ScatterChart as ScatterIcon,
  Table as TableIcon
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';
import { fetchChartData, ApiError } from '../../lib/api';
import type { RecommendedChart, ChartDataResponse } from '../../lib/api';
import { useDashboard } from '../../store/dashboardStore';

interface RenderedChartCardProps {
  chartConfig: RecommendedChart;
  fileId: string;
}

const PALETTE = [
  '#3b82f6', // blue
  '#10b981', // emerald
  '#8b5cf6', // purple
  '#f59e0b', // amber
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316'  // orange
];

export const RenderedChartCard: React.FC<RenderedChartCardProps> = ({ chartConfig, fileId }) => {
  const [chartData, setChartData] = useState<ChartDataResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const { addItem, removeItem, isInDashboard } = useDashboard();

  const itemId = `chart_${chartConfig.title}`;
  const inDashboard = isInDashboard(itemId);

  const handleToggleDashboard = () => {
    if (inDashboard) {
      removeItem(itemId);
    } else {
      addItem({
        id: itemId,
        type: 'chart',
        chartData: chartConfig,
      });
    }
  };

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    fetchChartData(fileId, chartConfig)
      .then((res) => {
        if (isMounted) {
          setChartData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err instanceof ApiError ? err.message : 'Failed to load chart data.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [fileId, chartConfig]);

  const getChartIcon = (type: string) => {
    switch (type) {
      case 'line':
        return <LineIcon className="w-4 h-4 text-primary" />;
      case 'scatter':
        return <ScatterIcon className="w-4 h-4 text-purple-500" />;
      case 'donut':
      case 'pie':
        return <PieIcon className="w-4 h-4 text-emerald-500" />;
      case 'table':
        return <TableIcon className="w-4 h-4 text-amber-500" />;
      default:
        return <BarChart3 className="w-4 h-4 text-blue-500" />;
    }
  };

  const renderVisual = () => {
    if (!chartData || chartData.data.length === 0) {
      return (
        <div className="w-full h-64 border border-hairline rounded-xl flex items-center justify-center bg-canvas text-muted text-xs font-medium">
          No data available for this chart configuration.
        </div>
      );
    }

    const isHorizontalBar = chartConfig.chart_type === 'bar';

    // 1. BAR / COLUMN CHARTS
    if (chartConfig.chart_type === 'bar' || chartConfig.chart_type === 'column') {
      return (
        <div className="w-full h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData.data}
              layout={isHorizontalBar ? 'vertical' : 'horizontal'}
              margin={{ top: 10, right: 20, left: isHorizontalBar ? 40 : 0, bottom: 25 }}
            >
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              {isHorizontalBar ? (
                <>
                  <XAxis type="number" tick={{ fontSize: 11, fill: 'currentColor' }} />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: 'currentColor' }} width={90} />
                </>
              ) : (
                <>
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'currentColor' }} />
                  <YAxis tick={{ fontSize: 11, fill: 'currentColor' }} />
                </>
              )}
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.9)',
                  borderColor: '#334155',
                  borderRadius: '12px',
                  color: '#f8fafc',
                  fontSize: '12px',
                }}
                formatter={(value: any) => [
                  typeof value === 'number' ? value.toLocaleString() : value,
                  chartConfig.y_axis
                ]}
              />
              <Bar dataKey="value" fill="#3b82f6" radius={isHorizontalBar ? [0, 6, 6, 0] : [6, 6, 0, 0]}>
                {chartData.data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={PALETTE[index % PALETTE.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      );
    }

    // 2. LINE CHARTS
    if (chartConfig.chart_type === 'line') {
      return (
        <div className="w-full h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData.data} margin={{ top: 10, right: 20, left: 0, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'currentColor' }} />
              <YAxis tick={{ fontSize: 11, fill: 'currentColor' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.9)',
                  borderColor: '#334155',
                  borderRadius: '12px',
                  color: '#f8fafc',
                  fontSize: '12px',
                }}
                formatter={(value: any) => [
                  typeof value === 'number' ? value.toLocaleString() : value,
                  chartConfig.y_axis
                ]}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#3b82f6"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#3b82f6' }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      );
    }

    // 3. SCATTER PLOTS
    if (chartConfig.chart_type === 'scatter') {
      return (
        <div className="w-full h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 10, right: 20, left: 0, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis
                type="number"
                dataKey="x"
                name={chartConfig.x_axis}
                tick={{ fontSize: 11, fill: 'currentColor' }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name={chartConfig.y_axis}
                tick={{ fontSize: 11, fill: 'currentColor' }}
              />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.9)',
                  borderColor: '#334155',
                  borderRadius: '12px',
                  color: '#f8fafc',
                  fontSize: '12px',
                }}
                formatter={(value: any, name: any) => [
                  typeof value === 'number' ? value.toLocaleString() : value,
                  name
                ]}
              />
              <Scatter name={`${chartConfig.x_axis} vs ${chartConfig.y_axis}`} data={chartData.data} fill="#8b5cf6" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      );
    }

    // 4. DONUT CHARTS
    if (chartConfig.chart_type === 'donut' || chartConfig.chart_type === 'pie') {
      return (
        <div className="w-full h-72 flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData.data}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={4}
              >
                {chartData.data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={PALETTE[index % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.9)',
                  borderColor: '#334155',
                  borderRadius: '12px',
                  color: '#f8fafc',
                  fontSize: '12px',
                }}
                formatter={(value: any) => [
                  typeof value === 'number' ? value.toLocaleString() : value,
                  chartConfig.y_axis
                ]}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      );
    }

    // 5. TABLE / MATRIX TYPE
    return (
      <div className="overflow-x-auto border border-hairline rounded-xl max-h-64 overflow-y-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="bg-canvas sticky top-0 z-10 border-b border-hairline text-caption font-semibold text-muted">
            <tr>
              <th className="py-2.5 px-3">{chartConfig.x_axis}</th>
              <th className="py-2.5 px-3 text-right">
                {chartConfig.aggregation !== 'NONE' ? `${chartConfig.aggregation}(${chartConfig.y_axis})` : chartConfig.y_axis}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline">
            {chartData.data.map((row, idx) => (
              <tr key={idx} className="hover:bg-surface-soft/60 transition-colors">
                <td className="py-2 px-3 font-mono font-medium text-ink truncate max-w-[180px]">
                  {row.name ?? row.x}
                </td>
                <td className="py-2 px-3 text-right font-mono font-semibold text-ink">
                  {row.value !== undefined ? row.value.toLocaleString() : row.y?.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="flex flex-col justify-between p-6 rounded-2xl border border-hairline bg-surface-card shadow-xs space-y-4">
      {/* Header */}
      <div>
        <div className="flex items-start justify-between gap-3 mb-1">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary-light text-primary flex items-center justify-center shrink-0">
              {getChartIcon(chartConfig.chart_type)}
            </div>
            <h3 className="text-title-sm text-ink font-bold leading-tight">
              {chartConfig.title}
            </h3>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-surface-soft text-primary border border-hairline uppercase">
              {chartConfig.chart_type}
            </span>
            {chartConfig.top_n && (
              <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                Top {chartConfig.top_n}
              </span>
            )}
            <button
              onClick={handleToggleDashboard}
              className={`py-1 px-2.5 text-xs gap-1 rounded-lg font-semibold border transition-all flex items-center ${
                inDashboard
                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20'
                  : 'btn-secondary'
              }`}
              title={inDashboard ? 'Remove from Dashboard' : 'Add to Dashboard'}
            >
              {inDashboard ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-500" />
                  <span className="hidden sm:inline">In Dashboard</span>
                </>
              ) : (
                <>
                  <PlusCircle className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Add</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Axis Tags */}
        <div className="flex flex-wrap items-center gap-2 mt-2 text-xs font-mono text-muted">
          <span className="bg-canvas px-2 py-0.5 rounded border border-hairline">
            X: {chartConfig.x_axis}
          </span>
          <span className="bg-canvas px-2 py-0.5 rounded border border-hairline">
            Y: {chartConfig.y_axis} ({chartConfig.aggregation})
          </span>
        </div>
      </div>

      {/* Main Chart Body */}
      {loading && (
        <div className="w-full h-72 border border-hairline rounded-xl flex items-center justify-center bg-canvas">
          <div className="flex items-center gap-2.5 text-muted text-xs font-medium">
            <Loader2 className="w-4 h-4 text-primary animate-spin" />
            <span>Calculating aggregated data for {chartConfig.title}...</span>
          </div>
        </div>
      )}

      {error && !loading && (
        <div className="p-4 rounded-xl border border-error/30 bg-error-bg/30 text-error text-xs font-medium space-y-1">
          <div className="flex items-center gap-1.5 font-bold">
            <AlertTriangle className="w-4 h-4" />
            <span>Chart Data Error</span>
          </div>
          <p className="text-body-sm">{error}</p>
        </div>
      )}

      {!loading && !error && renderVisual()}

      {/* Reason Footer */}
      <div className="pt-3 border-t border-hairline text-caption text-muted flex items-start gap-1.5">
        <Info className="w-3.5 h-3.5 text-primary shrink-0 mt-0.5" />
        <p className="leading-normal font-medium">{chartConfig.reason}</p>
      </div>
    </div>
  );
};
