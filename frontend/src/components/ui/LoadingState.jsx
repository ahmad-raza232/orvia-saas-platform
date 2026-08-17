const LoadingState = ({ label = 'Loading...' }) => (
  <div className="flex min-h-[50vh] items-center justify-center px-4">
    <div className="text-center">
      <div
        className="mx-auto h-10 w-10 rounded-full border-2 border-olive/20 border-t-olive animate-spin"
        aria-hidden="true"
      />
      <p className="mt-4 text-sm text-ink-secondary">{label}</p>
    </div>
  </div>
);

export default LoadingState;
