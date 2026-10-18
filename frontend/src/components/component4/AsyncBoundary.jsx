import LoadingSpinner from '../common/LoadingSpinner';
import ErrorState from '../common/ErrorState';
import EmptyState from '../common/EmptyState';

export default function AsyncBoundary({
  loading,
  error,
  data,
  onRetry,
  isEmpty = false,
  loadingMessage = 'Loading forecast data...',
  emptyTitle = 'No data available',
  emptyMessage = 'No data is available for the current selection.',
  children,
}) {
  if (loading && !data) return <LoadingSpinner message={loadingMessage} />;

  if (error) {
    if (error.status === 404) {
      return <EmptyState title={emptyTitle} message={emptyMessage} />;
    }
    return (
      <ErrorState
        title="Unable to load data"
        message={error.message || 'Please check the backend connection.'}
        onRetry={onRetry}
      />
    );
  }

  if (!data || isEmpty) {
    return <EmptyState title={emptyTitle} message={emptyMessage} />;
  }

  return (
    <div className={loading ? 'opacity-60 transition-opacity' : ''}>
      {children}
    </div>
  );
}
