// Pure function helper testing hydration safety logic
export const parseSavedDashboardItems = (raw: string | null): any[] => {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

export const runTests = () => {
  const tests = [
    {
      name: 'valid array JSON',
      input: JSON.stringify([{ id: '1', type: 'kpi' }]),
      expectedLength: 1,
    },
    {
      name: 'null raw value',
      input: null,
      expectedLength: 0,
    },
    {
      name: 'empty string raw value',
      input: '',
      expectedLength: 0,
    },
    {
      name: 'legacy non-array object state',
      input: JSON.stringify({ items: { '0': { id: '1' } } }),
      expectedLength: 0,
    },
    {
      name: 'primitive JSON values (number, boolean, string)',
      input: JSON.stringify(12345),
      expectedLength: 0,
    },
    {
      name: 'malformed JSON string',
      input: '{ malformed json ...',
      expectedLength: 0,
    },
  ];

  let passed = 0;
  for (const t of tests) {
    const res = parseSavedDashboardItems(t.input);
    if (Array.isArray(res) && res.length === t.expectedLength) {
      console.log(`[PASS] ${t.name}`);
      passed++;
    } else {
      console.error(`[FAIL] ${t.name}: expected length ${t.expectedLength}, got`, res);
    }
  }
  return passed === tests.length;
};
