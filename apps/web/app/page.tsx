'use client';

import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react';

type TabId = 'calendar' | 'household' | 'settings';

const TABS: { id: TabId; label: string; badge?: string }[] = [
  { id: 'calendar', label: 'Calendar', badge: 'Weekly view' },
  { id: 'household', label: 'Household', badge: 'People & preferences' },
  { id: 'settings', label: 'Settings', badge: 'Dev tools' }
];

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const CALENDAR_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const DAY_ORDER = CALENDAR_DAYS;
const MEAL_SLOTS = ['Breakfast', 'Lunch', 'Dinner'];

type MealPlanEntry = {
  id: number;
  plan_id: number;
  day: string;
  slot: string;
  title?: string | null;
  summary?: string | null;
  ingredients?: Ingredient[];
  steps?: string[];
  prep_minutes?: number | null;
  cook_minutes?: number | null;
  calories_per_person?: number | null;
  attendee_ids?: number[];
  guest_count?: number | null;
};

type MealPlan = {
  id: number;
  household_id: number;
  week_start: string;
  eco_friendly: boolean;
  use_leftovers: boolean;
  notes?: string | null;
  timeline?: AgentTimelineEvent[] | null;
  entries: MealPlanEntry[];
};

type MealPlanSummary = {
  id: number;
  household_id: number;
  week_start: string;
  eco_friendly: boolean;
  use_leftovers: boolean;
  created_at: string;
};

type AgentTimelineEvent = {
  agent?: string;
  stage?: string;
  payload?: Record<string, unknown>;
  [key: string]: unknown;
};

type AgentTimelineMeta = {
  label: string;
  kind: 'sequential' | 'parallel';
  description: string;
  inputs: string[];
  outputs: string[];
};

type PlannerMessage = {
  id: string;
  role: 'agent' | 'user';
  text: string;
};

type CalendarTabProps = {
  apiBaseUrl: string;
};

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<TabId>('calendar');

  return (
    <div className="space-y-6">
      <header className="rounded-3xl border border-slate-800/70 bg-slate-900/70 p-6 shadow-futuristic backdrop-blur-xl md:p-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/40 bg-cyan-500/10 px-3 py-1 text-[0.7rem] font-medium uppercase tracking-[0.2em] text-cyan-200">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-300 shadow-[0_0_12px_rgba(34,211,238,0.9)]" />
              EcoFood · Agents-Driven Meal Planner
            </div>
            <h1 className="mt-4 bg-gradient-to-r from-cyan-300 via-sky-400 to-emerald-300 bg-clip-text text-3xl font-semibold tracking-tight text-transparent md:text-5xl">
              Eat better, with less thinking.
            </h1>
            <p className="mt-3 max-w-xl text-sm text-slate-300 md:text-base">
              EcoFood orchestrates multiple AI agents to design safe, diverse,
              and pantry-aware weekly menus for your household — tuned to
              allergens, tastes, and time.
            </p>
          </div>

          <div className="space-y-3 text-xs text-slate-300 md:text-sm">
            <div className="flex flex-wrap gap-2">
              <span className="rounded-full border border-cyan-400/40 bg-cyan-500/10 px-3 py-1 text-cyan-200">
                Multi-agent orchestration
              </span>
              <span className="rounded-full border border-emerald-400/40 bg-emerald-500/10 px-3 py-1 text-emerald-200">
                Gemini-powered planning
              </span>
              <span className="rounded-full border border-sky-400/40 bg-sky-500/10 px-3 py-1 text-sky-200">
                Nutritional nudges
              </span>
            </div>
            <ol className="space-y-1">
              <li>
                <span className="font-semibold text-cyan-300">1.</span> Configure{' '}
                <code className="rounded bg-slate-900/80 px-1.5 py-0.5 text-[0.7rem] text-cyan-200">
                  GEMINI_API_KEY
                </code>{' '}
                in your <code>.env</code>.
              </li>
              <li>
                <span className="font-semibold text-cyan-300">2.</span> Capture
                your household and pantry.
              </li>
              <li>
                <span className="font-semibold text-cyan-300">3.</span> Let the
                planner propose a smarter week.
              </li>
            </ol>
          </div>
        </div>

        <nav className="mt-6 flex flex-wrap gap-2 rounded-full bg-slate-950/60 p-1 text-xs text-slate-300 shadow-inner shadow-slate-900/60 md:text-sm">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 rounded-full px-3 py-1.5 transition-colors md:px-4 ${
                  isActive
                    ? 'bg-cyan-500 text-slate-950 shadow-[0_0_18px_rgba(34,211,238,0.6)]'
                    : 'bg-transparent text-slate-300 hover:bg-slate-900/80 hover:text-cyan-200'
                }`}
              >
                <span className="font-medium">{tab.label}</span>
                {tab.badge && (
                  <span
                    className={`hidden rounded-full border px-2 py-0.5 text-[0.65rem] md:inline ${
                      isActive
                        ? 'border-slate-900/60 bg-slate-900/40 text-cyan-100'
                        : 'border-slate-700 bg-slate-900/40 text-slate-400'
                    }`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </header>

      <section className="rounded-3xl border border-slate-800/70 bg-slate-950/80 p-5 backdrop-blur-xl md:p-6">
        {activeTab === 'calendar' && (
          <CalendarTab apiBaseUrl={API_BASE_URL} />
        )}
        {activeTab === 'household' && (
          <HouseholdTab apiBaseUrl={API_BASE_URL} />
        )}
        {activeTab === 'settings' && (
          <SettingsTab apiBaseUrl={API_BASE_URL} />
        )}
      </section>
    </div>
  );
}

function CalendarTab({ apiBaseUrl }: CalendarTabProps) {
  const [households, setHouseholds] = useState<Household[]>([]);
  const [selectedHouseholdId, setSelectedHouseholdId] = useState<number | null>(
    null
  );
  const [weekSummaries, setWeekSummaries] = useState<MealPlanSummary[]>([]);
  const [currentWeekStart, setCurrentWeekStart] = useState<string>(() =>
    startOfWeekISO(new Date())
  );
  const [plan, setPlan] = useState<MealPlan | null>(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [plannerBusy, setPlannerBusy] = useState(false);
  const [ecoFriendly, setEcoFriendly] = useState(false);
  const [useLeftovers, setUseLeftovers] = useState(true);
  const [notes, setNotes] = useState('');
  const [timeline, setTimeline] = useState<AgentTimelineEvent[]>([]);
  const [sessionViewerOpen, setSessionViewerOpen] = useState(false);
  const [agentBriefOpen, setAgentBriefOpen] = useState(false);
  const [shoppingModalOpen, setShoppingModalOpen] = useState(false);
  const [planningOverlayOpen, setPlanningOverlayOpen] = useState(false);
  const [planningMessages, setPlanningMessages] = useState<string[]>([]);
  const [activePlanJobId, setActivePlanJobId] = useState<number | null>(null);
  const [currentPlanningDay, setCurrentPlanningDay] = useState<string | null>(null);
  const [planningError, setPlanningError] = useState<string | null>(null);
  const planJobSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [plannerMessages, setPlannerMessages] = useState<PlannerMessage[]>([]);
  const [plannerInput, setPlannerInput] = useState('');
  const [plannerChatBusy, setPlannerChatBusy] = useState(false);
  const [mealViewer, setMealViewer] = useState<{
    open: boolean;
    entry: MealPlanEntry | null;
    dayLabel: string;
    slot: string;
  }>({
    open: false,
    entry: null,
    dayLabel: '',
    slot: ''
  });
  const [entryEditor, setEntryEditor] = useState<{
    open: boolean;
    entry: MealPlanEntry | null;
    dayLabel: string;
    slot: string;
    title: string;
    summary: string;
    attendeeIds: number[];
    guestCount: number;
  }>({
    open: false,
    entry: null,
    dayLabel: '',
    slot: '',
    title: '',
    summary: '',
    attendeeIds: [],
    guestCount: 0
  });
  const [entrySaving, setEntrySaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const clearPlanJobChannel = useCallback(() => {
    if (planJobSourceRef.current) {
      planJobSourceRef.current.close();
      planJobSourceRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const appendPlanningMessage = useCallback((text: string) => {
    setPlanningMessages((prev) => [...prev, text]);
  }, []);
  const leftoversPromptedRef = useRef(false);

  const selectedHousehold = useMemo(
    () =>
      households.find((household) => household.id === selectedHouseholdId) ??
      null,
    [households, selectedHouseholdId]
  );
  const memberNameLookup = useMemo(() => {
    const map = new Map<number, string>();
    selectedHousehold?.members.forEach((member) => map.set(member.id, member.name));
    return map;
  }, [selectedHousehold]);

  const entriesBySlot = useMemo(() => {
    const map = new Map<string, MealPlanEntry>();
    plan?.entries.forEach((entry) => {
      const key = `${isoDayLabel(entry.day)}-${entry.slot}`;
      map.set(key, entry);
    });
    return map;
  }, [plan]);
  const shoppingList = useMemo(() => {
    const finalEvent = timeline.find(
      (event) => event.stage === 'plan.final' || event.agent === 'plan-synthesizer'
    );
    if (!finalEvent || !finalEvent.payload || typeof finalEvent.payload !== 'object') {
      return null;
    }
    const shopping = (finalEvent.payload as Record<string, any>).shopping_list;
    if (!shopping || typeof shopping !== 'object') {
      return null;
    }
    const groups = shopping.groups && typeof shopping.groups === 'object' ? shopping.groups : {};
    const listAll = Array.isArray(shopping.all) ? shopping.all : [];
    return { groups, all: listAll };
  }, [timeline]);
  const calendarExport = useMemo(() => {
    const finalEvent = timeline.find(
      (event) => event.stage === 'plan.final' || event.agent === 'plan-synthesizer'
    );
    if (!finalEvent || !finalEvent.payload || typeof finalEvent.payload !== 'object') {
      return null;
    }
    const calendar = (finalEvent.payload as Record<string, any>).calendar;
    if (!calendar || typeof calendar !== 'object') {
      return null;
    }
    return calendar;
  }, [timeline]);
  const shoppingText = useMemo(() => {
    if (!shoppingList) {
      return '';
    }
    const sections = Object.entries(shoppingList.groups as Record<string, string[]>).map(
      ([section, items]) => `${section.replace(/_/g, ' ')}:\n- ${items.join('\n- ')}`
    );
    const sectionsText = sections.join('\n\n');
    const flat = shoppingList.all.length
      ? `\n\nAll items:\n- ${shoppingList.all.join('\n- ')}`
      : '';
    return `${sectionsText}${flat}`.trim();
  }, [shoppingList]);
  const handleCopyShoppingList = useCallback(() => {
    if (!shoppingText) {
      return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(shoppingText).then(
        () => setMessage('Shopping list copied to clipboard.'),
        () => setError('Unable to copy shopping list.')
      );
    }
  }, [shoppingText]);
  const handleDownloadShoppingList = useCallback(() => {
    if (!shoppingText) {
      return;
    }
    const blob = new Blob([shoppingText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ecofood-groceries-${currentWeekStart}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [shoppingText, currentWeekStart]);
  const handleDownloadCalendar = useCallback(() => {
    if (!calendarExport || typeof calendarExport.ics !== 'string') {
      return;
    }
    const blob = new Blob([calendarExport.ics], { type: 'text/calendar' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ecofood-week-${currentWeekStart}.ics`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [calendarExport, currentWeekStart]);

  const applyPartialEntries = useCallback(
    (entries: MealPlanEntry[]) => {
      if (!entries.length) {
        return;
      }
      setPlan((prev) => {
        const basePlan: MealPlan =
          prev ?? {
            id: -1,
            household_id: selectedHouseholdId ?? -1,
            week_start: currentWeekStart,
            eco_friendly: ecoFriendly,
            use_leftovers: useLeftovers,
            notes,
            timeline: [],
            entries: []
          };
        const map = new Map<string, MealPlanEntry>();
        basePlan.entries.forEach((entry) => {
          map.set(`${entry.day}-${entry.slot}`, entry);
        });
        entries.forEach((entry) => {
          map.set(`${entry.day}-${entry.slot}`, entry);
        });
        return { ...basePlan, entries: Array.from(map.values()) };
      });
    },
    [selectedHouseholdId, currentWeekStart, ecoFriendly, useLeftovers, notes]
  );

  const describeAttendees = useCallback(
    (entry: MealPlanEntry) => {
      const attendeeIds = entry.attendee_ids ?? [];
      const names = attendeeIds
        .map((id) => memberNameLookup.get(id))
        .filter((name): name is string => Boolean(name));
      const guestCount = entry.guest_count ?? 0;
      const summaryParts = [];
      if (names.length) {
        summaryParts.push(names.join(', '));
      }
      if (guestCount > 0) {
        summaryParts.push(`${guestCount} guest${guestCount === 1 ? '' : 's'}`);
      }
      const servings = attendeeIds.length + guestCount;
      return {
        summary: summaryParts.length ? summaryParts.join(' • ') : 'No diners assigned',
        servings,
      };
    },
    [memberNameLookup]
  );

  const appendPlannerMessage = useCallback(
    (role: 'agent' | 'user', text: string) => {
      setPlannerMessages((prev) => [
        ...prev,
        {
          id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          role,
          text
        }
      ]);
    },
    []
  );

  useEffect(() => {
    const label = weekRangeLabel(currentWeekStart);
    setPlannerMessages([
      {
        id: `agent-week-${currentWeekStart}`,
        role: 'agent',
        text: `New planning session for ${label}. Share constraints or ideas before we update the meals.`
      }
    ]);
    setPlannerInput('');
    leftoversPromptedRef.current = false;
  }, [currentWeekStart, selectedHouseholdId]);

  useEffect(() => {
    if (useLeftovers && !leftoversPromptedRef.current) {
      leftoversPromptedRef.current = true;
      appendPlannerMessage(
        'agent',
        'Since we want to save waste, list any leftovers or ingredients expiring soon so I can push them to the agents.'
      );
    } else if (!useLeftovers) {
      leftoversPromptedRef.current = false;
    }
  }, [useLeftovers, appendPlannerMessage]);

  const handlePlannerChatSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!plannerInput.trim()) {
      return;
    }
    const text = plannerInput.trim();
    appendPlannerMessage('user', text);
    setPlannerInput('');
    setPlannerChatBusy(true);
    setTimeout(() => {
      appendPlannerMessage(
        'agent',
        useLeftovers
          ? `Great, I'll prioritize those leftovers: "${text}". Anything else I should consider?`
          : `Logged your note: "${text}". I'll blend it into the planning brief.`
      );
      setPlannerChatBusy(false);
    }, 600);
  };

  const PlannerChatPanel = ({ compact = false }: { compact?: boolean }) => (
    <div className="flex flex-col rounded-2xl border border-slate-800 bg-slate-950/60 p-3 text-sm text-slate-100">
      <div className="flex items-center justify-between text-[0.7rem] uppercase tracking-[0.3em] text-slate-400">
        <span>Planner chat</span>
        <span className="text-slate-500">
          {plannerChatBusy ? 'thinking…' : 'live'}
        </span>
      </div>
      <div
        className={`mt-2 space-y-2 overflow-y-auto pr-1 text-xs text-slate-200 ${
          compact ? 'max-h-40' : 'max-h-48'
        }`}
      >
        {plannerMessages.map((msg) => (
          <div
            key={msg.id}
            className={`rounded-2xl border px-3 py-2 ${
              msg.role === 'agent'
                ? 'border-cyan-500/30 bg-cyan-500/5 text-cyan-100'
                : 'border-slate-700/80 bg-slate-900/70 text-slate-200'
            }`}
          >
            <p className="text-[0.65rem] uppercase tracking-[0.3em] text-slate-400">
              {msg.role === 'agent' ? 'agent' : 'you'}
            </p>
            <p className="mt-1 text-[0.75rem]">{msg.text}</p>
          </div>
        ))}
      </div>
      <form
        onSubmit={handlePlannerChatSubmit}
        className="mt-3 flex items-center gap-2 text-xs"
      >
        <input
          value={plannerInput}
          onChange={(event) => setPlannerInput(event.target.value)}
          placeholder="Tell the planner what you need..."
          className="flex-1 rounded-2xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 focus:border-cyan-400 focus:outline-none"
        />
        <button
          type="submit"
          disabled={!plannerInput.trim() || plannerChatBusy}
          className="rounded-2xl border border-cyan-400/60 px-4 py-2 text-xs font-semibold text-cyan-100 hover:bg-cyan-500/10 disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </div>
  );

  const AgentBriefControls = () => (
    <>
      <label className="flex items-start gap-3 text-sm text-slate-200">
        <input
          type="checkbox"
          checked={ecoFriendly}
          onChange={(event) => setEcoFriendly(event.target.checked)}
          className="mt-1 h-4 w-4 rounded border-slate-700 bg-slate-950 text-cyan-400 focus:ring-cyan-400"
        />
        <span>
          Prioritize eco-friendly recipes
          <span className="block text-xs text-slate-400">
            Adds a bias toward plant-forward meals & low-impact proteins.
          </span>
        </span>
      </label>
      <label className="flex items-start gap-3 text-sm text-slate-200">
        <input
          type="checkbox"
          checked={useLeftovers}
          onChange={(event) => setUseLeftovers(event.target.checked)}
          className="mt-1 h-4 w-4 rounded border-slate-700 bg-slate-950 text-emerald-400 focus:ring-emerald-400"
        />
        <span>
          Save waste (use leftovers)
          <span className="block text-xs text-slate-400">
            The planner will request pantry inputs and prioritize ingredients nearing
            expiry.
          </span>
        </span>
      </label>
      <div>
        <label className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
          Notes to agents
        </label>
        <textarea
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          rows={3}
          placeholder="Ex: highlight comfort food on Friday night."
          className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 focus:border-cyan-400 focus:outline-none"
        />
      </div>
    </>
  );

  const fetchHouseholds = useCallback(async () => {
    setError(null);
    try {
      const res = await fetch(`${apiBaseUrl}/households`);
      if (!res.ok) {
        throw new Error('Unable to load households');
      }
      let data: Household[] = await res.json();
      if (!data.length) {
        const createRes = await fetch(`${apiBaseUrl}/households`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: 'My household' })
        });
        if (!createRes.ok) {
          throw new Error('Unable to create a default household');
        }
        const created: Household = await createRes.json();
        data = [created];
      }
      setHouseholds(data);
      setSelectedHouseholdId((prev) => {
        if (prev && data.some((household) => household.id === prev)) {
          return prev;
        }
        return data[0]?.id ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load households');
    }
  }, [apiBaseUrl]);

  const fetchSummaries = useCallback(
    async (householdId: number) => {
      try {
        const res = await fetch(
          `${apiBaseUrl}/households/${householdId}/plans`
        );
        if (!res.ok) {
          throw new Error('Unable to load previous weeks');
        }
        const data: MealPlanSummary[] = await res.json();
        setWeekSummaries(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load plans');
      }
    },
    [apiBaseUrl]
  );

  const fetchPlanForWeek = useCallback(
    async (householdId: number, weekStartISO: string) => {
      setPlanLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `${apiBaseUrl}/households/${householdId}/plans/${weekStartISO}`
        );
        if (res.status === 404) {
          setPlan(null);
          setTimeline([]);
          return;
        }
        if (!res.ok) {
          throw new Error('Unable to load meal plan');
        }
        const data: MealPlan = await res.json();
        setPlan(data);
        setTimeline(Array.isArray(data.timeline) ? data.timeline : []);
        setEcoFriendly(data.eco_friendly);
        setUseLeftovers(data.use_leftovers);
        setNotes(data.notes ?? '');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load plan');
      } finally {
        setPlanLoading(false);
      }
    },
    [apiBaseUrl]
  );

  const subscribeToPlanJob = useCallback(
    function subscribe(jobId: number, resume = false) {
      clearPlanJobChannel();
      const source = new EventSource(
        `${apiBaseUrl}/plan-jobs/${jobId}/events/stream`
      );
      planJobSourceRef.current = source;
      setActivePlanJobId(jobId);
      setPlanningOverlayOpen(true);
      setPlanningError(null);
      if (!resume) {
        setPlanningMessages([`Job #${jobId} queued`]);
      }

      source.onmessage = (event) => {
        if (!event.data) {
          return;
        }
        try {
          const payload = JSON.parse(event.data);
          if (payload.message) {
            appendPlanningMessage(payload.message);
          }
          if (payload.stage === 'planning' && typeof payload.payload?.day === 'string') {
            setCurrentPlanningDay(payload.payload.day);
          }
          if (payload.stage === 'planned') {
            setCurrentPlanningDay(null);
          }
          if (payload.payload?.entries) {
            applyPartialEntries(payload.payload.entries as MealPlanEntry[]);
          }
          if (payload.stage === 'completed') {
            appendPlanningMessage('Job completed. Refreshing plan…');
            clearPlanJobChannel();
            setActivePlanJobId(null);
            setCurrentPlanningDay(null);
            if (selectedHouseholdId) {
              fetchPlanForWeek(selectedHouseholdId, currentWeekStart);
              fetchSummaries(selectedHouseholdId);
            }
            setPlanningOverlayOpen(false);
          } else if (payload.stage === 'error') {
            setPlanningError(
              typeof payload.payload?.error === 'string'
                ? payload.payload.error
                : payload.message ?? 'Planning failed'
            );
            clearPlanJobChannel();
            setActivePlanJobId(null);
            setCurrentPlanningDay(null);
            setPlanningOverlayOpen(true);
          } else if (payload.stage === 'cancelled') {
            appendPlanningMessage('Job cancelled.');
            clearPlanJobChannel();
            setActivePlanJobId(null);
            setCurrentPlanningDay(null);
            setPlanningOverlayOpen(false);
          }
        } catch (err) {
          appendPlanningMessage('Malformed event payload');
        }
      };

      source.onerror = () => {
        appendPlanningMessage('Connection lost. Retrying…');
        clearPlanJobChannel();
        reconnectTimerRef.current = setTimeout(() => {
          subscribe(jobId, true);
        }, 1500);
      };
    },
    [
      apiBaseUrl,
      appendPlanningMessage,
      applyPartialEntries,
      clearPlanJobChannel,
      currentWeekStart,
      fetchPlanForWeek,
      fetchSummaries,
      selectedHouseholdId
    ]
  );

  useEffect(() => {
    fetchHouseholds();
  }, [fetchHouseholds]);

  useEffect(() => {
    if (selectedHouseholdId) {
      fetchSummaries(selectedHouseholdId);
    }
  }, [selectedHouseholdId, fetchSummaries]);

  useEffect(() => {
    if (selectedHouseholdId) {
      fetchPlanForWeek(selectedHouseholdId, currentWeekStart);
    }
  }, [selectedHouseholdId, currentWeekStart, fetchPlanForWeek]);

  useEffect(() => {
    return () => {
      clearPlanJobChannel();
    };
  }, [clearPlanJobChannel]);

  const shiftWeek = useCallback(
    (delta: number) => {
      clearPlanJobChannel();
      setActivePlanJobId(null);
      setCurrentPlanningDay(null);
      setPlanningMessages([]);
      setPlanningError(null);
      setPlanningOverlayOpen(false);
      setCurrentWeekStart((prev) => {
        const next = new Date(`${prev}T00:00:00`);
        next.setDate(next.getDate() + delta * 7);
        return startOfWeekISO(next);
      });
    },
    [clearPlanJobChannel]
  );

  const handlePlanWeek = async () => {
    if (!selectedHouseholdId) {
      return;
    }
    clearPlanJobChannel();
    setPlanningMessages([]);
    setPlanningError(null);
    setCurrentPlanningDay(null);
    setActivePlanJobId(null);
    setPlannerBusy(true);
    setMessage('Agents are crafting the week...');
    try {
      const res = await fetch(`${apiBaseUrl}/plan-jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          household_id: selectedHouseholdId,
          week_start: currentWeekStart,
          eco_friendly: ecoFriendly,
          use_leftovers: useLeftovers,
          notes
        })
      });
      if (!res.ok) {
        throw new Error('Meal planning failed. Check household data.');
      }
      const job = await res.json();
      appendPlanningMessage(`Job #${job.id} accepted. Planning ${DAY_ORDER[0]}…`);
      subscribeToPlanJob(job.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to plan meals');
    } finally {
      setPlannerBusy(false);
    }
  };

  const handleAbortPlanning = useCallback(async () => {
    if (!activePlanJobId) {
      setPlanningOverlayOpen(false);
      return;
    }
    appendPlanningMessage('Abort requested by user.');
    try {
      const res = await fetch(`${apiBaseUrl}/plan-jobs/${activePlanJobId}`, {
        method: 'DELETE'
      });
      if (!res.ok && res.status !== 404 && res.status !== 409) {
        throw new Error('Unable to cancel planning job');
      }
    } catch (err) {
      setPlanningError(err instanceof Error ? err.message : 'Failed to cancel job');
    } finally {
      clearPlanJobChannel();
      setActivePlanJobId(null);
      setCurrentPlanningDay(null);
      setPlanningOverlayOpen(false);
    }
  }, [activePlanJobId, apiBaseUrl, appendPlanningMessage, clearPlanJobChannel]);

  const handleResetWeek = async () => {
    if (!selectedHouseholdId) {
      return;
    }
    setPlannerBusy(true);
    setMessage('Resetting this week…');
    try {
      const res = await fetch(
        `${apiBaseUrl}/households/${selectedHouseholdId}/plans/${currentWeekStart}`,
        { method: 'DELETE' }
      );
      if (res.ok || res.status === 404) {
        setPlan(null);
        setTimeline([]);
        if (selectedHouseholdId) {
          await fetchSummaries(selectedHouseholdId);
        }
        setMessage('Week cleared. Ready for a fresh plan.');
      } else {
        throw new Error('Failed to reset plan');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reset week');
    } finally {
      setPlannerBusy(false);
    }
  };

  const openMealViewer = (dayLabel: string, slot: string) => {
    const entry = entriesBySlot.get(`${dayLabel}-${slot}`) ?? null;
    if (!entry) {
      setMessage('No recipe yet for this slot. Plan the week to fill it.');
      return;
    }
    setMealViewer({
      open: true,
      entry,
      dayLabel,
      slot
    });
  };

  const closeEntryEditor = () =>
    setEntryEditor({
      open: false,
      entry: null,
      dayLabel: '',
      slot: '',
      title: '',
      summary: '',
      attendeeIds: [],
      guestCount: 0
    });

  const closeMealViewer = () =>
    setMealViewer({
      open: false,
      entry: null,
      dayLabel: '',
      slot: ''
    });

  const startEntryEditor = (entry: MealPlanEntry, dayLabel: string, slot: string) => {
    appendPlannerMessage(
      'agent',
      `Loading this week's session: let's refine ${slot} on ${dayLabel}. What would you like to change?`
    );
    const defaultAttendees =
      entry.attendee_ids && entry.attendee_ids.length
        ? [...entry.attendee_ids]
        : selectedHousehold
          ? selectedHousehold.members.map((member) => member.id)
          : [];
    setEntryEditor({
      open: true,
      entry,
      dayLabel,
      slot,
      title: entry.title ?? '',
      summary: entry.summary ?? '',
      attendeeIds: defaultAttendees,
      guestCount: entry.guest_count ?? 0
    });
  };

  const editFromViewer = () => {
    if (!mealViewer.entry) {
      return;
    }
    startEntryEditor(mealViewer.entry, mealViewer.dayLabel, mealViewer.slot);
    closeMealViewer();
  };

  const toggleEntryAttendee = (memberId: number) => {
    setEntryEditor((state) => {
      const exists = state.attendeeIds.includes(memberId);
      const attendeeIds = exists
        ? state.attendeeIds.filter((id) => id !== memberId)
        : [...state.attendeeIds, memberId];
      return { ...state, attendeeIds };
    });
  };

  const adjustGuestCount = (delta: number) => {
    setEntryEditor((state) => ({
      ...state,
      guestCount: Math.max(0, state.guestCount + delta)
    }));
  };

  const viewerIngredients = useMemo<Ingredient[]>(() => {
    if (mealViewer.entry?.ingredients && mealViewer.entry.ingredients.length) {
      return mealViewer.entry.ingredients;
    }
    return [
      { name: 'Seasonal vegetables' },
      { name: 'Protein of choice' },
      { name: 'Whole grains' },
      { name: 'Fresh herbs' }
    ];
  }, [mealViewer]);

  const viewerSteps = useMemo(() => {
    if (mealViewer.entry?.steps && mealViewer.entry.steps.length) {
      return mealViewer.entry.steps;
    }
    return [
      'Prep aromatics and chop vegetables.',
      'Warm cookware and start aromatics.',
      'Add remaining ingredients and cook until done.',
      'Finish with herbs or citrus, then serve.'
    ];
  }, [mealViewer]);

  const submitEntryEditor = async (event: FormEvent) => {
    event.preventDefault();
    if (!entryEditor.entry) {
      return;
    }
    if (entryEditor.attendeeIds.length === 0 && entryEditor.guestCount === 0) {
      setError('Select at least one household member or guest for this meal.');
      return;
    }
    setEntrySaving(true);
    try {
      const res = await fetch(
        `${apiBaseUrl}/meal-plan-entries/${entryEditor.entry.id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: entryEditor.title,
            summary: entryEditor.summary,
            attendee_ids: entryEditor.attendeeIds,
            guest_count: entryEditor.guestCount
          })
        }
      );
      if (!res.ok) {
        throw new Error('Unable to update meal');
      }
      const updated: MealPlanEntry = await res.json();
      setPlan((prev) =>
        prev
          ? {
              ...prev,
              entries: prev.entries.map((item) =>
                item.id === updated.id ? updated : item
              )
            }
          : prev
      );
      closeEntryEditor();
      setMessage('Meal updated for this slot.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update meal');
    } finally {
      setEntrySaving(false);
    }
  };

  return (
    <>
      <div className="space-y-5">
        <div className="flex flex-col gap-4 rounded-2xl border border-slate-800/80 bg-slate-950/70 p-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-[0.7rem] font-semibold uppercase tracking-[0.25em] text-slate-400">
              Weekly agent planner
            </p>
            <h2 className="mt-1 text-xl font-semibold text-slate-50 md:text-2xl">
              {selectedHousehold ? `Plan for ${selectedHousehold.name}` : 'Loading household…'}
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              Configure eco-friendly nudges, leftovers awareness, and let the agents populate this
              calendar.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-200">
            <select
              value={selectedHouseholdId ?? ''}
              onChange={(event) =>
                setSelectedHouseholdId(event.target.value ? Number(event.target.value) : null)
              }
              className="rounded-2xl border border-slate-700 bg-slate-900/70 px-3 py-2 text-sm text-slate-100 focus:border-cyan-400 focus:outline-none"
            >
              {households.map((household) => (
                <option key={household.id} value={household.id}>
                  {household.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => setSessionViewerOpen(true)}
              disabled={!timeline.length}
              className="rounded-2xl border border-cyan-400/50 bg-cyan-500/10 px-4 py-2 text-xs font-semibold text-cyan-100 shadow-[0_0_18px_rgba(34,211,238,0.35)] hover:bg-cyan-500/20 disabled:border-slate-700 disabled:text-slate-500"
            >
              {timeline.length ? 'Open agent session' : 'No session yet'}
            </button>
            <button
              onClick={() => setShoppingModalOpen(true)}
              disabled={!shoppingList}
              className="rounded-2xl border border-emerald-400/50 bg-emerald-500/10 px-4 py-2 text-xs font-semibold text-emerald-100 shadow-[0_0_18px_rgba(52,211,153,0.35)] hover:bg-emerald-500/20 disabled:border-slate-700 disabled:text-slate-500"
            >
              Export groceries
            </button>
            <button
              onClick={handleDownloadCalendar}
              disabled={!calendarExport?.ics}
              className="rounded-2xl border border-slate-400/50 bg-slate-500/10 px-4 py-2 text-xs font-semibold text-slate-100 hover:bg-slate-500/20 disabled:border-slate-700 disabled:text-slate-500"
            >
              Download calendar (.ics)
            </button>
          </div>
        </div>

        {(error || message) && (
          <div
            className={`rounded-2xl border px-4 py-3 text-sm ${
              error
                ? 'border-rose-500/40 bg-rose-500/10 text-rose-100'
                : 'border-emerald-400/40 bg-emerald-500/10 text-emerald-100'
            }`}
          >
            {error ?? message}
          </div>
        )}

        <div className="space-y-4 lg:col-span-2">
          <div className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-950/60 p-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.25em] text-slate-500">
                Week of {currentWeekStart}
              </p>
              <h3 className="text-lg font-semibold text-slate-100">{weekRangeLabel(currentWeekStart)}</h3>
              <p className="text-xs text-slate-400">
                {plan
                  ? 'Plan saved — edit any slot or re-run the agents.'
                  : 'Empty week. Plan it with the agents or review a past week.'}
              </p>
            </div>
          <div className="flex items-center gap-2 text-xs">
            <button
              onClick={() => shiftWeek(-1)}
              className="rounded-full border border-slate-700 px-3 py-1.5 text-slate-300 hover:border-cyan-400 hover:text-cyan-100"
            >
              ◀ Previous
            </button>
            <button
              onClick={() => shiftWeek(1)}
              className="rounded-full border border-slate-700 px-3 py-1.5 text-slate-300 hover:border-cyan-400 hover:text-cyan-100"
            >
              Next ▶
            </button>
            <button
              onClick={handleResetWeek}
              disabled={!plan || plannerBusy}
              className="rounded-full border border-rose-400/60 px-3 py-1.5 text-rose-100 hover:border-rose-400 hover:text-rose-200 disabled:opacity-40"
            >
              Reset week
            </button>
          </div>
        </div>

          <div className="relative rounded-2xl border border-slate-800 bg-slate-950/70 p-2 md:p-3">
            {planLoading && (
              <div className="absolute inset-0 z-10 flex items-center justify-center rounded-2xl bg-slate-950/80 text-sm text-slate-200">
                Syncing with backend…
              </div>
            )}
            <div className="grid grid-cols-[minmax(60px,80px)_repeat(7,minmax(0,1fr))] gap-[1px] text-[0.65rem]">
              <div className="flex items-center justify-start rounded-xl bg-slate-950/90 px-2 py-2 text-[0.6rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
                Meal
              </div>
              {CALENDAR_DAYS.map((day) => (
                <div
                  key={day}
                  className="flex items-center justify-center rounded-xl bg-slate-950/90 px-1.5 py-2 text-[0.6rem] font-semibold uppercase tracking-[0.2em] text-slate-400"
                >
                  {day}
                </div>
              ))}

              {MEAL_SLOTS.map((slot) => (
                <div key={slot} className="contents">
                  <div className="flex items-start justify-start rounded-xl bg-slate-950/90 px-2 py-3 text-[0.65rem] font-medium text-slate-200">
                    {slot}
                  </div>
                  {CALENDAR_DAYS.map((day) => {
                    const entry = entriesBySlot.get(`${day}-${slot}`);
                    const hasEntry = Boolean(entry);
                    const entryHighlightsLeftovers = Boolean(
                      entry?.summary?.toLowerCase().includes('pantry')
                    );
                    const attendanceInfo = entry ? describeAttendees(entry) : null;
                    const servingsLabel =
                      attendanceInfo && attendanceInfo.servings > 0
                        ? `${attendanceInfo.servings} serving${attendanceInfo.servings === 1 ? '' : 's'}`
                        : '';
                    return (
                      <div
                        key={`${day}-${slot}`}
                        role="button"
                        tabIndex={0}
                        onClick={() => openMealViewer(day, slot)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            openMealViewer(day, slot);
                          }
                        }}
                        className={`rounded-2xl border border-slate-800/70 bg-slate-900/70 p-2 text-[0.65rem] text-slate-200 transition-colors ${
                          hasEntry
                            ? 'cursor-pointer hover:border-cyan-400/50'
                            : 'cursor-pointer opacity-70 hover:border-slate-700'
                        }`}
                      >
                        <p className="line-clamp-2 font-semibold text-slate-100">
                          {entry?.title ?? 'Empty slot'}
                        </p>
                        {attendanceInfo && (
                          <p className="mt-1 line-clamp-2 text-[0.6rem] text-slate-400">
                            {attendanceInfo.summary}
                            {servingsLabel ? ` · ${servingsLabel}` : ''}
                          </p>
                        )}
                        <div className="mt-2 flex items-center justify-between text-[0.55rem]">
                          <span className="text-slate-400">
                            {hasEntry ? 'Click to refine' : 'Click to add'}
                          </span>
                          {entry && (
                            <button
                              type="button"
                              onClick={(event) => {
                                event.stopPropagation();
                                startEntryEditor(entry, day, slot);
                              }}
                              className="rounded-full border border-slate-700/70 px-2 py-0.5 text-[0.55rem] text-slate-300 hover:border-cyan-400 hover:text-cyan-100"
                            >
                              Manage diners
                            </button>
                          )}
                          {plan && plan.use_leftovers && entryHighlightsLeftovers && (
                            <span className="rounded-full border border-emerald-400/40 px-2 py-0.5 text-emerald-200">
                              Leftovers
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-6 space-y-4 rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-inner shadow-slate-950/40">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-400">
                Meal planner
              </h3>
              <p className="text-sm text-slate-300">
                Configure options and chat before launching the agents.
              </p>
            </div>
            <button
              onClick={() => setAgentBriefOpen(true)}
              className="rounded-full border border-cyan-400/50 px-3 py-1 text-[0.7rem] text-cyan-100 hover:bg-cyan-500/10"
            >
              Pop out
            </button>
          </div>
          <div className="grid gap-4 lg:grid-cols-[1.2fr,1fr]">
            <div className="space-y-4">
              <AgentBriefControls />
              <button
                onClick={handlePlanWeek}
                disabled={!selectedHouseholdId || plannerBusy || Boolean(activePlanJobId)}
                className="w-full rounded-2xl bg-gradient-to-r from-cyan-500 to-emerald-400 px-4 py-2 text-center text-sm font-semibold text-slate-950 shadow-[0_0_30px_rgba(34,211,238,0.45)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {plannerBusy
                  ? 'Coordinating agents…'
                  : activePlanJobId
                    ? 'Planner running…'
                    : 'Plan this week'}
              </button>
            </div>
            <PlannerChatPanel />
          </div>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-400">
              Session timeline
            </h3>
            {timeline.length ? (
              <>
                <div className="space-y-2">
                  {timeline.slice(0, 3).map((event, index) => (
                    <TimelineCard key={`${event.stage}-${index}`} event={event} compact />
                  ))}
                </div>
                {timeline.length > 3 && (
                  <button
                    onClick={() => setSessionViewerOpen(true)}
                    className="text-xs text-cyan-300 underline-offset-4 hover:underline"
                  >
                    View full conversation ({timeline.length} steps)
                  </button>
                )}
              </>
            ) : (
              <p className="text-sm text-slate-400">
                Once you run the planner, each agent stage will be archived here.
              </p>
            )}
          </div>
          <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-400">
              Saved weeks
            </h3>
            {weekSummaries.length ? (
              <div className="flex flex-wrap gap-2">
                {weekSummaries.map((summary) => {
                  const isActive = summary.week_start === currentWeekStart;
                  return (
                    <button
                      key={summary.id}
                      onClick={() => setCurrentWeekStart(summary.week_start)}
                      className={`rounded-full border px-3 py-1 text-xs ${
                        isActive
                          ? 'border-cyan-400/60 bg-cyan-500/10 text-cyan-100'
                          : 'border-slate-700 bg-slate-950/80 text-slate-300 hover:border-cyan-400/40 hover:text-cyan-100'
                      }`}
                    >
                      {weekRangeLabel(summary.week_start)}
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-slate-400">
                No past plans yet. Run the planner to start a historical log.
              </p>
            )}
          </div>
        </div>
      </div>

      {agentBriefOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/80 px-4 py-6">
          <div className="w-full max-w-xl rounded-3xl border border-slate-800 bg-slate-950/90 p-5 text-sm text-slate-100 shadow-[0_0_45px_rgba(34,211,238,0.25)]">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
                  Meal planner · Advanced view
                </p>
                <h4 className="text-lg font-semibold text-slate-50">
                  {selectedHousehold ? `Household: ${selectedHousehold.name}` : 'Household settings'}
                </h4>
              </div>
              <button
                onClick={() => setAgentBriefOpen(false)}
                className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-cyan-400 hover:text-cyan-100"
              >
                Close
              </button>
            </div>
            <div className="mt-4 space-y-4">
              <div className="space-y-4">
                <AgentBriefControls />
                <PlannerChatPanel />
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-xs text-slate-300">
                  <p className="font-semibold text-slate-200">Advanced directives (coming soon)</p>
                  <ul className="mt-2 list-disc space-y-1 pl-4">
                    <li>Limit total prep time per day.</li>
                    <li>Force agent to ask pantry follow-ups twice.</li>
                    <li>Bias toward cultural themes or cuisines.</li>
                  </ul>
                </div>
                <button
                  onClick={handlePlanWeek}
                  disabled={!selectedHouseholdId || plannerBusy}
                  className="w-full rounded-2xl bg-gradient-to-r from-cyan-500 to-emerald-400 px-4 py-2 text-center text-sm font-semibold text-slate-950 shadow-[0_0_30px_rgba(34,211,238,0.45)] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {plannerBusy ? 'Coordinating agents…' : 'Plan this week'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {mealViewer.open && mealViewer.entry && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/80 px-4 py-6">
          <div className="w-full max-w-2xl rounded-3xl border border-slate-800 bg-slate-950/90 p-5 text-sm text-slate-100 shadow-[0_0_45px_rgba(15,118,255,0.25)]">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Meal details</p>
                <h4 className="text-lg font-semibold text-slate-50">
                  {mealViewer.dayLabel} · {mealViewer.slot}
                </h4>
              </div>
              <button
                onClick={closeMealViewer}
                className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-cyan-400 hover:text-cyan-100"
              >
                Close
              </button>
            </div>
            <div className="mt-4 space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <h5 className="text-xs uppercase tracking-[0.25em] text-slate-400">Ingredients</h5>
                <ul className="mt-3 list-disc space-y-1 pl-4 text-sm text-slate-200">
                  {viewerIngredients.map((ingredient, idx) => (
                    <li key={`${ingredient.name}-${idx}`}>
                      <span className="font-medium text-slate-100">{ingredient.name}</span>
                      {(ingredient.quantity || ingredient.unit) && (
                        <span className="text-slate-400">
                          {' '}
                          — {ingredient.quantity ?? ''} {ingredient.unit ?? ''}
                        </span>
                      )}
                      {ingredient.notes && (
                        <span className="text-slate-500"> ({ingredient.notes})</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <h5 className="text-xs uppercase tracking-[0.25em] text-slate-400">Recipe</h5>
                <div className="mt-2 flex flex-wrap gap-3 text-[0.7rem] text-slate-300">
                  {mealViewer.entry.prep_minutes != null && (
                    <span className="rounded-full border border-slate-700 px-2 py-0.5">
                      Prep: {mealViewer.entry.prep_minutes} min
                    </span>
                  )}
                  {mealViewer.entry.cook_minutes != null && (
                    <span className="rounded-full border border-slate-700 px-2 py-0.5">
                      Cook: {mealViewer.entry.cook_minutes} min
                    </span>
                  )}
                  {mealViewer.entry.calories_per_person != null && (
                    <span className="rounded-full border border-slate-700 px-2 py-0.5">
                      {mealViewer.entry.calories_per_person} kcal / person
                    </span>
                  )}
                </div>
                <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-200">
                  {viewerSteps.map((step, idx) => (
                    <li key={`${idx}-${step.slice(0, 8)}`}>{step}</li>
                  ))}
                </ol>
                {mealViewer.entry.summary && (
                  <p className="mt-2 text-xs text-slate-400">
                    Notes: {mealViewer.entry.summary}
                  </p>
                )}
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <h5 className="text-xs uppercase tracking-[0.25em] text-slate-400">Cooking hints</h5>
                <ul className="mt-3 list-disc space-y-1 pl-4 text-sm text-slate-200">
                  <li>Prep aromatics and sauces first to reduce stove time later.</li>
                  {plan?.use_leftovers ? (
                    <li>Swap in leftover produce to keep waste low—just adjust seasoning to taste.</li>
                  ) : (
                    <li>Roast veggies for deeper flavor before combining everything.</li>
                  )}
                  <li>Aim for plating within 25 minutes; hold sauces warm in a covered pan.</li>
                </ul>
              </div>
              <button
                onClick={editFromViewer}
                className="w-full rounded-2xl border border-cyan-400/60 bg-cyan-500/10 px-4 py-2 text-center text-sm font-semibold text-cyan-100 hover:bg-cyan-500/20"
              >
                Edit this meal
              </button>
            </div>
      </div>
    </div>
  )}

  {planningOverlayOpen && (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/80 px-4 py-6">
      <div className="w-full max-w-lg rounded-3xl border border-slate-800 bg-slate-950/90 p-5 text-sm text-slate-100 shadow-[0_0_45px_rgba(34,211,238,0.35)]">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Loop agent status</p>
            <p className="text-[0.7rem] text-slate-500">
              {activePlanJobId ? `Job #${activePlanJobId}` : 'Awaiting next run'}
            </p>
          </div>
          <button
            onClick={() => {
              if (!activePlanJobId) {
                setPlanningOverlayOpen(false);
              }
            }}
            className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-400 hover:border-cyan-400 hover:text-cyan-100 disabled:opacity-40"
            disabled={Boolean(activePlanJobId)}
          >
            Close
          </button>
        </div>
        {currentPlanningDay && (
          <p className="mt-3 text-sm text-cyan-200">
            Planning {currentPlanningDay}…
          </p>
        )}
        {planningError && (
          <p className="mt-3 rounded-2xl border border-rose-500/50 bg-rose-500/10 px-3 py-2 text-xs text-rose-100">
            {planningError}
          </p>
        )}
        <div className="mt-3 max-h-64 space-y-2 overflow-y-auto pr-2 text-xs text-slate-200">
          {planningMessages.map((msg, idx) => (
            <p key={`${msg}-${idx}`}>{msg}</p>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          {activePlanJobId && (
            <button
              onClick={handleAbortPlanning}
              className="rounded-full border border-rose-400/50 px-4 py-2 text-rose-100 hover:border-rose-300 hover:text-rose-200"
            >
              Abort planning
            </button>
          )}
          {planningError && !activePlanJobId && (
            <button
              onClick={() => {
                setPlanningOverlayOpen(false);
                handlePlanWeek();
              }}
              className="rounded-full border border-cyan-400/50 px-4 py-2 text-cyan-100 hover:border-cyan-300 hover:text-cyan-50"
            >
              Retry now
            </button>
          )}
          {!activePlanJobId && !planningError && (
            <button
              onClick={() => setPlanningOverlayOpen(false)}
              className="rounded-full border border-slate-700 px-4 py-2 text-slate-300 hover:border-cyan-400 hover:text-cyan-100"
            >
              Hide overlay
            </button>
          )}
        </div>
      </div>
    </div>
  )}

  {sessionViewerOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/80 px-4 py-6">
          <div className="w-full max-w-3xl rounded-3xl border border-slate-800 bg-slate-950/90 p-5 text-sm text-slate-100 shadow-[0_0_45px_rgba(15,118,255,0.25)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Agent session</p>
                <h4 className="text-lg font-semibold text-slate-50">
                  {weekRangeLabel(currentWeekStart)}
                </h4>
              </div>
              <button
                onClick={() => setSessionViewerOpen(false)}
                className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-cyan-400 hover:text-cyan-100"
              >
                Close
              </button>
            </div>
            <div className="mt-4 max-h-[60vh] space-y-3 overflow-y-auto pr-3">
              {timeline.map((event, index) => (
                <TimelineCard key={`${event.agent}-${event.stage}-${index}`} event={event} />
              ))}
            </div>
          </div>
        </div>
      )}

      {shoppingModalOpen && shoppingList && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/80 px-4 py-6">
          <div className="w-full max-w-3xl rounded-3xl border border-slate-800 bg-slate-950/90 p-5 text-sm text-slate-100 shadow-[0_0_45px_rgba(16,185,129,0.25)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Groceries export</p>
                <h4 className="text-lg font-semibold text-slate-50">
                  {weekRangeLabel(currentWeekStart)}
                </h4>
              </div>
              <button
                onClick={() => setShoppingModalOpen(false)}
                className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-emerald-400 hover:text-emerald-100"
              >
                Close
              </button>
            </div>
            <div className="mt-4 max-h-[45vh] space-y-3 overflow-y-auto pr-2">
              {Object.entries(shoppingList.groups as Record<string, string[]>).map(
                ([section, items]) => (
                  <div
                    key={section}
                    className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4"
                  >
                    <p className="text-[0.65rem] uppercase tracking-[0.25em] text-slate-400">
                      {section.replace(/_/g, ' ')}
                    </p>
                    <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-slate-100">
                      {items.map((item) => (
                        <li key={`${section}-${item}`}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )
              )}
              {!Object.keys(shoppingList.groups as Record<string, string[]>).length && (
                <p className="text-sm text-slate-400">No grouped items available.</p>
              )}
            </div>
            <textarea
              readOnly
              value={shoppingText}
              className="mt-4 h-32 w-full rounded-2xl border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-200"
            />
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                onClick={handleCopyShoppingList}
                className="flex-1 rounded-2xl border border-cyan-400/60 px-4 py-2 text-center text-xs font-semibold text-cyan-100 hover:bg-cyan-500/10 disabled:opacity-40"
                disabled={!shoppingText}
              >
                Copy to clipboard
              </button>
              <button
                onClick={handleDownloadShoppingList}
                className="flex-1 rounded-2xl border border-emerald-400/60 px-4 py-2 text-center text-xs font-semibold text-emerald-100 hover:bg-emerald-500/10 disabled:opacity-40"
                disabled={!shoppingText}
              >
                Download .txt
              </button>
            </div>
          </div>
        </div>
      )}

      {entryEditor.open && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/80 px-4 py-6">
          <div className="w-full max-w-3xl rounded-3xl border border-slate-800 bg-slate-950/90 p-5 text-sm text-slate-100 shadow-[0_0_45px_rgba(15,118,255,0.25)]">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
                  Edit meal · Chat-enabled
                </p>
                <h4 className="text-lg font-semibold text-slate-50">
                  {entryEditor.dayLabel} · {entryEditor.slot}
                </h4>
              </div>
              <button
                type="button"
                onClick={closeEntryEditor}
                className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-rose-400 hover:text-rose-100"
              >
                Close
              </button>
            </div>
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <form onSubmit={submitEntryEditor} className="space-y-4">
                <div>
                  <label className="text-xs uppercase tracking-[0.2em] text-slate-400">Title</label>
                  <input
                    value={entryEditor.title}
                    onChange={(event) =>
                      setEntryEditor((state) => ({
                        ...state,
                        title: event.target.value
                      }))
                    }
                    className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 focus:border-cyan-400 focus:outline-none"
                    placeholder="Name of the meal"
                  />
                </div>
                <div>
                  <label className="text-xs uppercase tracking-[0.2em] text-slate-400">Summary</label>
                  <textarea
                    value={entryEditor.summary}
                    onChange={(event) =>
                      setEntryEditor((state) => ({
                        ...state,
                        summary: event.target.value
                      }))
                    }
                    rows={5}
                    className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 focus:border-cyan-400 focus:outline-none"
                    placeholder="Notes, prep reminders, or nutrition highlights."
                  />
                </div>
                {selectedHousehold && (
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <label className="text-xs uppercase tracking-[0.2em] text-slate-400">
                      Who&apos;s eating
                    </label>
                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      {selectedHousehold.members.map((member) => (
                        <label
                          key={member.id}
                          className="flex items-center gap-2 rounded-xl border border-slate-800/70 bg-slate-950/40 px-3 py-2 text-sm text-slate-200"
                        >
                          <input
                            type="checkbox"
                            checked={entryEditor.attendeeIds.includes(member.id)}
                            onChange={() => toggleEntryAttendee(member.id)}
                            className="h-4 w-4 rounded border-slate-700 bg-slate-950 text-cyan-500 focus:ring-cyan-400"
                          />
                          <span>{member.name}</span>
                        </label>
                      ))}
                    </div>
                    <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-slate-200">
                      <span className="text-xs uppercase tracking-[0.2em] text-slate-400">
                        Guests
                      </span>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => adjustGuestCount(-1)}
                          className="h-8 w-8 rounded-full border border-slate-700 text-base text-slate-200 hover:border-cyan-400"
                        >
                          –
                        </button>
                        <span className="w-10 text-center text-lg font-semibold text-slate-50">
                          {entryEditor.guestCount}
                        </span>
                        <button
                          type="button"
                          onClick={() => adjustGuestCount(1)}
                          className="h-8 w-8 rounded-full border border-slate-700 text-base text-slate-200 hover:border-cyan-400"
                        >
                          +
                        </button>
                      </div>
                      <span className="text-xs text-slate-400">
                        Total servings: {entryEditor.attendeeIds.length + entryEditor.guestCount}
                      </span>
                    </div>
                  </div>
                )}
                <button
                  type="submit"
                  disabled={entrySaving}
                  className="w-full rounded-2xl bg-gradient-to-r from-cyan-500 to-emerald-400 px-4 py-2 text-center text-sm font-semibold text-slate-950 shadow-[0_0_30px_rgba(34,211,238,0.45)] disabled:opacity-50"
                >
                  {entrySaving ? 'Saving…' : 'Save changes'}
                </button>
              </form>
              <div>
                <PlannerChatPanel compact />
              </div>
            </div>
          </div>
        </div>
      )}

    </>
  );
}

function TimelineCard({
  event,
  compact = false
}: {
  event: AgentTimelineEvent;
  compact?: boolean;
}) {
  const meta = event.agent ? AGENT_TIMELINE_REGISTRY[event.agent] : undefined;
  const detailLines = buildTimelineDetails(event);
  const visibleLines = compact ? detailLines.slice(0, 2) : detailLines;
  const hiddenCount = compact ? detailLines.length - visibleLines.length : 0;
  const stageLabel = event.stage ?? 'Agent stage';
  const agentLabel = meta?.label ?? formatAgentName(event.agent ?? 'Agent');

  return (
    <div
      className={
        compact
          ? 'rounded-2xl border border-slate-700/80 bg-slate-950/60 p-3 text-xs text-slate-200'
          : 'rounded-2xl border border-slate-800 bg-slate-900/70 p-4 text-sm text-slate-200'
      }
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[0.6rem] uppercase tracking-[0.25em] text-slate-500">
            {meta ? 'LLM A2A agent' : 'Agent'}
          </p>
          <p className="text-base font-semibold tracking-tight text-slate-50">
            {agentLabel}
          </p>
          {meta && (
            <p className="text-[0.65rem] text-slate-400">{meta.description}</p>
          )}
        </div>
        <div className="text-right">
          <p className="text-[0.6rem] uppercase tracking-[0.25em] text-slate-500">
            {stageLabel}
          </p>
          <span
            className={`mt-1 inline-flex items-center justify-center rounded-full border px-2 py-0.5 text-[0.6rem] ${
              meta?.kind === 'parallel'
                ? 'border-purple-400/50 text-purple-200'
                : 'border-cyan-400/50 text-cyan-100'
            }`}
          >
            {meta ? `${meta.kind === 'parallel' ? 'Parallel' : 'Sequential'} A2A` : 'A2A step'}
          </span>
        </div>
      </div>
      {visibleLines.length ? (
        <ul className="mt-3 space-y-1 text-[0.7rem] text-slate-200">
          {visibleLines.map((line, index) => (
            <li key={`${stageLabel}-${index}`} className="flex gap-2">
              <span className="mt-1 h-1.5 w-1.5 rounded-full bg-cyan-400/70" />
              <span className="flex-1">{line}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-[0.7rem] text-slate-400">
          Payload available in session logs.
        </p>
      )}
      {compact && hiddenCount > 0 && (
        <p className="mt-2 text-[0.6rem] text-slate-400">
          +{hiddenCount} more insight
          {hiddenCount === 1 ? '' : 's'} inside the session viewer.
        </p>
      )}
      {!compact && meta && (
        <div className="mt-3 rounded-2xl border border-slate-800/70 bg-slate-950/40 p-3 text-[0.65rem] text-slate-300">
          <p className="text-[0.55rem] uppercase tracking-[0.25em] text-slate-500">
            Action schema
          </p>
          <div className="mt-2 flex flex-col gap-1">
            <p>
              <span className="text-slate-400">Inputs:</span>{' '}
              {meta.inputs.length ? meta.inputs.join(', ') : '—'}
            </p>
            <p>
              <span className="text-slate-400">Outputs:</span>{' '}
              {meta.outputs.length ? meta.outputs.join(', ') : '—'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function buildScheduleFromMeals(meals: string[]): MemberMealSchedule {
  const normalized = new Set(meals);
  const schedule: MemberMealSchedule = {} as MemberMealSchedule;
  CALENDAR_DAYS.forEach((day) => {
    schedule[day] = {};
    MEAL_SLOTS.forEach((slot) => {
      schedule[day][slot] = normalized.has(slot);
    });
  });
  return schedule;
}

function ensureScheduleStructure(
  schedule: MemberMealSchedule | null,
  fallbackMeals: string[]
): MemberMealSchedule {
  if (!schedule) {
    return buildScheduleFromMeals(fallbackMeals);
  }
  const normalized: MemberMealSchedule = {} as MemberMealSchedule;
  CALENDAR_DAYS.forEach((day) => {
    normalized[day] = {};
    MEAL_SLOTS.forEach((slot) => {
      normalized[day][slot] = Boolean(schedule[day]?.[slot]);
    });
  });
  return normalized;
}

function deriveMealsFromSchedule(schedule: MemberMealSchedule): string[] {
  const slots: string[] = [];
  MEAL_SLOTS.forEach((slot) => {
    if (CALENDAR_DAYS.some((day) => schedule[day]?.[slot])) {
      slots.push(slot);
    }
  });
  return slots;
}

function startOfWeekISO(value: Date): string {
  const date = new Date(value);
  const day = date.getDay(); // 0 (Sunday) to 6 (Saturday)
  const diff = day === 0 ? -6 : 1 - day;
  date.setHours(0, 0, 0, 0);
  date.setDate(date.getDate() + diff);
  return formatLocalISODate(date);
}

function weekRangeLabel(weekStartISO: string): string {
  const start = new Date(`${weekStartISO}T00:00:00`);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  const formatter = (value: Date) =>
    value.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  return `${formatter(start)} – ${formatter(end)}`;
}

function isoDayLabel(isoDate: string): string {
  const labels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const day = new Date(`${isoDate}T00:00:00`).getDay();
  return labels[day] ?? 'Mon';
}

function formatLocalISODate(date: Date): string {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function buildTimelineDetails(event: AgentTimelineEvent): string[] {
  const payload = event.payload;
  if (!payload || !isRecord(payload)) {
    return [];
  }

  const lines: string[] = [];

  switch (event.stage) {
    case 'profile.ready': {
      const profile = isRecord(payload.profile) ? payload.profile : null;
      if (profile) {
        const memberCount =
          typeof profile.member_count === 'number' ? profile.member_count : null;
        if (memberCount !== null) {
          lines.push(`${memberCount} member${memberCount === 1 ? '' : 's'} normalized for downstream agents.`);
        }
        const roles = isRecord(profile.roles)
          ? Object.entries(profile.roles).filter(
              ([, value]) => typeof value === 'number'
            )
          : [];
        if (roles.length) {
          const roleSummary = roles
            .map(([role, count]) => `${count}× ${role}`)
            .join(', ');
          lines.push(`Roles mapped: ${roleSummary}.`);
        }
        const allergens = Array.isArray(profile.allergens)
          ? profile.allergens
              .map((item) =>
                isRecord(item) && typeof item.name === 'string'
                  ? item.name
                  : null
              )
              .filter((name): name is string => Boolean(name))
          : [];
        if (allergens.length) {
          lines.push(
            `Tracked allergens: ${formatInlineList(allergens, 4)}.`
          );
        }
        const likes = Array.isArray(profile.top_likes)
          ? profile.top_likes
              .map((item) =>
                isRecord(item) && typeof item.name === 'string'
                  ? item.name
                  : null
              )
              .filter((name): name is string => Boolean(name))
          : [];
        if (likes.length) {
          lines.push(
            `Top cravings detected: ${formatInlineList(likes, 4)}.`
          );
        }
      }
      break;
    }
    case 'plan.candidate': {
      const planItems = Array.isArray(payload.plan)
        ? payload.plan.filter((item): item is Record<string, any> =>
            isRecord(item)
          )
        : [];
      if (planItems.length) {
        const dayCount = new Set(
          planItems
            .map((item) => (typeof item.day === 'string' ? item.day : null))
            .filter(Boolean)
        ).size;
        lines.push(
          `Meal architect drafted ${planItems.length} meals covering ${dayCount || '?'} day(s).`
        );
        const sample = planItems[0];
        const sampleTitle =
          typeof sample.title === 'string' ? sample.title : 'Meal';
        const sampleDay =
          typeof sample.day === 'string' ? sample.day : 'Day';
        const metrics = [
          typeof sample.prep_minutes === 'number'
            ? `${sample.prep_minutes}m prep`
            : null,
          typeof sample.cook_minutes === 'number'
            ? `${sample.cook_minutes}m cook`
            : null,
          typeof sample.calories_per_person === 'number'
            ? `${sample.calories_per_person} kcal/person`
            : null
        ]
          .filter(Boolean)
          .join(' · ');
        lines.push(
          `Example: ${sampleDay} – ${sampleTitle}${metrics ? ` (${metrics})` : ''}.`
        );
      }
      const source = typeof payload.source === 'string' ? payload.source : null;
      if (source === 'gemini') {
        lines.push('Plan generated via Gemini culinary model.');
      } else if (source === 'fallback') {
        lines.push('Fallback static recipe rotation was used.');
      }
      if (typeof payload.plan_id === 'string') {
        lines.push(`Plan stored under tag ${payload.plan_id}.`);
      }
      if (typeof payload.notes === 'string' && payload.notes.trim()) {
        lines.push(`Notes forwarded to architect: ${payload.notes.trim()}.`);
      }
      break;
    }
    case 'plan.enhanced': {
      const themes = Array.isArray(payload.themes)
        ? payload.themes.filter((t): t is string => typeof t === 'string')
        : [];
      if (themes.length) {
        lines.push(`Chef themes drafted: ${formatInlineList(themes, 3)}.`);
      }
      if (typeof payload.menu_story === 'string' && payload.menu_story.trim()) {
        lines.push(payload.menu_story.trim());
      }
      break;
    }
    case 'plan.review.nutrition': {
      const analysis = isRecord(payload.analysis) ? payload.analysis : null;
      if (analysis) {
        if (typeof analysis.summary === 'string') {
          lines.push(analysis.summary);
        }
        const estimate = isRecord(analysis.estimate)
          ? analysis.estimate
          : null;
        if (estimate) {
          const macros = [
            typeof estimate.calories_estimate === 'number'
              ? `${estimate.calories_estimate} kcal`
              : null,
            typeof estimate.protein_g === 'number'
              ? `${estimate.protein_g}g protein`
              : null,
            typeof estimate.carbs_g === 'number'
              ? `${estimate.carbs_g}g carbs`
              : null,
            typeof estimate.fat_g === 'number'
              ? `${estimate.fat_g}g fat`
              : null,
            typeof estimate.fiber_g === 'number'
              ? `${estimate.fiber_g}g fiber`
              : null
          ]
            .filter(Boolean)
            .join(' · ');
          if (macros) {
            lines.push(`Macro snapshot: ${macros}.`);
          }
        }
        const labels = Array.isArray(analysis.labels)
          ? analysis.labels.filter(
              (label): label is string => typeof label === 'string'
            )
          : [];
        if (labels.length) {
          lines.push(`Nutrition tags: ${labels.join(', ')}.`);
        }
      }
      break;
    }
    case 'plan.review.pantry': {
      const suggestions = isRecord(payload.suggestions)
        ? payload.suggestions
        : null;
      const suggestionList = suggestions && Array.isArray(suggestions.suggestions)
        ? suggestions.suggestions
        : [];
      lines.push(
        `Pantry reviewer proposed ${suggestionList.length} leftover usage${suggestionList.length === 1 ? '' : 's'}.`
      );
      if (suggestions && typeof suggestions.note === 'string' && suggestions.note.trim()) {
        lines.push(`Note: ${suggestions.note.trim()}`);
      }
      const annotated = Array.isArray(payload.annotated_plan)
        ? payload.annotated_plan.filter((item): item is Record<string, any> =>
            isRecord(item)
          )
        : [];
      const annotatedWithHint = annotated.find(
        (item) => typeof item.pantry_hint === 'string' && item.pantry_hint
      );
      if (annotatedWithHint) {
        const day =
          typeof annotatedWithHint.day === 'string'
            ? annotatedWithHint.day
            : 'Day';
        const title =
          typeof annotatedWithHint.title === 'string'
            ? annotatedWithHint.title
            : 'Meal';
        lines.push(
          `Example assignment: ${day} – ${title} ← ${annotatedWithHint.pantry_hint}.`
        );
      }
      break;
    }
    case 'plan.final': {
      const planItems = Array.isArray(payload.plan) ? payload.plan : [];
      const shoppingList = isRecord(payload.shopping_list)
        ? payload.shopping_list
        : null;
      const shoppingCount = Array.isArray(shoppingList?.all)
        ? shoppingList!.all.length
        : 0;
      const calendarInfo = isRecord(payload.calendar)
        ? payload.calendar
        : null;
      const calendarEvents =
        typeof calendarInfo?.event_count === 'number'
          ? calendarInfo.event_count
          : null;
      lines.push(
        `Synthesis locked ${planItems.length} meals, ${shoppingCount} shopping items, and ${calendarEvents ?? '?'} ICS events.`
      );
      const reviewKeys = isRecord(payload.reviews)
        ? Object.keys(payload.reviews)
        : [];
      if (reviewKeys.length) {
        lines.push(`Merged reviews: ${reviewKeys.join(', ')}.`);
      }
      break;
    }
    default:
      break;
  }

  if (!lines.length) {
    const fallback = truncatePayload(payload);
    if (fallback) {
      lines.push(fallback);
    }
  }

  return lines;
}

function formatInlineList(items: string[], limit = 3): string {
  const clean = items.filter((item) => item && item.trim());
  if (!clean.length) {
    return '';
  }
  if (clean.length === 1) {
    return clean[0];
  }
  const limited = clean.slice(0, limit);
  const head = limited.slice(0, -1).join(', ');
  const tail = limited[limited.length - 1];
  const sentence =
    limited.length > 1 ? `${head}${head ? ', and ' : ''}${tail}` : tail;
  if (clean.length > limit) {
    return `${sentence} (+${clean.length - limit} more)`;
  }
  return sentence;
}

function formatAgentName(raw: string): string {
  return raw
    .split(/[-_]/g)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function isRecord(value: unknown): value is Record<string, any> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function truncatePayload(payload: Record<string, unknown>): string {
  try {
    const raw = JSON.stringify(payload);
    return raw.length > 180 ? `${raw.slice(0, 177)}…` : raw;
  } catch {
    return 'Payload captured (unable to summarize).';
  }
}

const AGENT_TIMELINE_REGISTRY: Record<string, AgentTimelineMeta> = {
  'household-profiler': {
    label: 'Household profiler',
    kind: 'sequential',
    description:
      'LLM condenses members and dietary notes into a structured profile.',
    inputs: ['members (names, roles, allergens, likes)'],
    outputs: ['profile.member_count', 'profile.allergens', 'profile.top_likes']
  },
  'meal-architect': {
    label: 'Meal architect',
    kind: 'sequential',
    description:
      'LLM + recipe tools assemble a draft plan tailored to the profile and kitchen tools.',
    inputs: ['profile data', 'notes', 'kitchen_tools'],
    outputs: ['plan[] entries', 'plan_id']
  },
  'nutrition-reviewer': {
    label: 'Nutrition reviewer',
    kind: 'parallel',
    description:
      'Parallel agent computes heuristic macros and wellness tags for each plan.',
    inputs: ['plan summaries'],
    outputs: ['analysis.summary', 'analysis.estimate', 'analysis.labels']
  },
  'pantry-reviewer': {
    label: 'Pantry reviewer',
    kind: 'parallel',
    description:
      'Parallel agent matches soon-to-expire ingredients to the drafted plan.',
    inputs: ['plan[]', 'pantry_items'],
    outputs: ['suggestions[]', 'annotated_plan[]']
  },
  'plan-synthesizer': {
    label: 'Plan synthesizer',
    kind: 'sequential',
    description:
      'Final agent merges reviews, builds shopping lists, and exports calendar data.',
    inputs: ['plan', 'nutrition_review', 'pantry_review'],
    outputs: ['shopping_list', 'calendar.ics', 'final_plan']
  },
  'chef-curator': {
    label: 'Chef curator',
    kind: 'sequential',
    description:
      'LLM-inspired chef elevates the menu with themes, pairings, and plating cues.',
    inputs: ['architect plan[]', 'household profile', 'notes'],
    outputs: ['plan[] with chef_theme/pairing', 'menu_story']
  }
};


type Member = {
  id: number;
  name: string;
  role: string;
  allergens: string[];
  likes: string[];
  meal_schedule?: MemberMealSchedule | null;
  meals: string[];
};

type KitchenTool = {
  id: number;
  label: string;
  category?: string | null;
  quantity: number;
};

type Ingredient = {
  name: string;
  quantity?: string | number | null;
  unit?: string | null;
  notes?: string | null;
};

type Household = {
  id: number;
  name: string;
  created_at: string;
  members: Member[];
  kitchen_tools: KitchenTool[];
};

type AssistantMessage = {
  id: string;
  role: 'agent' | 'user';
  text: string;
};

type MemberMealSchedule = Record<string, Record<string, boolean>>;

type HouseholdTabProps = {
  apiBaseUrl: string;
};

function HouseholdTab({ apiBaseUrl }: HouseholdTabProps) {
  const [households, setHouseholds] = useState<Household[]>([]);
  const [selectedHouseholdId, setSelectedHouseholdId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [role, setRole] = useState<string>('Adult');
  const [allergensInput, setAllergensInput] = useState('');
  const [likesInput, setLikesInput] = useState('');

  const [assistantOpen, setAssistantOpen] = useState(false);
  const [assistantStage, setAssistantStage] = useState('');
  const [assistantSessionId, setAssistantSessionId] = useState<string | null>(null);
  const [assistantInput, setAssistantInput] = useState('');
  const [assistantMessages, setAssistantMessages] = useState<AssistantMessage[]>([]);
  const [assistantBusy, setAssistantBusy] = useState(false);
  const [toolLabel, setToolLabel] = useState('');
  const [toolCategory, setToolCategory] = useState('');
  const [toolQuantity, setToolQuantity] = useState(1);
  const [kitchenBusy, setKitchenBusy] = useState(false);
  const [newHouseholdName, setNewHouseholdName] = useState('');
  const [creatingHousehold, setCreatingHousehold] = useState(false);
  const [mealEditor, setMealEditor] = useState<{
    open: boolean;
    member: Member | null;
    selections: string[];
    advanced: boolean;
    schedule: MemberMealSchedule;
    saving: boolean;
    error: string | null;
  }>({
    open: false,
    member: null,
    selections: [...MEAL_SLOTS],
    advanced: false,
    schedule: buildScheduleFromMeals(MEAL_SLOTS),
    saving: false,
    error: null
  });

  const selectedHousehold =
    households.find((household) => household.id === selectedHouseholdId) ?? null;
  const kitchenTools = selectedHousehold?.kitchen_tools ?? [];

  const householdSummary = useMemo(() => {
    if (!selectedHousehold) {
      return { total: 0, allergens: [] as string[] };
    }
    const labels = new Set<string>();
    selectedHousehold.members.forEach((member) =>
      member.allergens.forEach((label) => labels.add(label))
    );
    return { total: selectedHousehold.members.length, allergens: Array.from(labels) };
  }, [selectedHousehold]);

  const fetchHouseholds = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBaseUrl}/households`);
      if (!res.ok) {
        throw new Error(`Failed to load households (${res.status})`);
      }
      let data: Household[] = await res.json();
      if (!data.length) {
        const createRes = await fetch(`${apiBaseUrl}/households`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: 'My household' })
        });
        if (!createRes.ok) {
          throw new Error('Unable to create default household');
        }
        const created: Household = await createRes.json();
        data = [created];
      }
      setHouseholds(data);
      setSelectedHouseholdId((prev) => prev ?? data[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    fetchHouseholds();
  }, [fetchHouseholds]);

  const handleAddMember = async () => {
    if (!selectedHousehold || !name.trim()) {
      return;
    }
    try {
      const payload = {
        name: name.trim(),
        role,
        allergens: allergensInput
          .split(',')
          .map((label) => label.trim())
          .filter(Boolean),
        likes: likesInput
          .split(',')
          .map((label) => label.trim())
          .filter(Boolean)
      };
      const res = await fetch(
        `${apiBaseUrl}/households/${selectedHousehold.id}/members`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }
      );
      if (!res.ok) {
        throw new Error('Failed to add member');
      }
      setName('');
      setRole('Adult');
      setAllergensInput('');
      setLikesInput('');
      await fetchHouseholds();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add member');
    }
  };

  const handleRemoveMember = async (memberId: number) => {
    if (!selectedHousehold) {
      return;
    }
    try {
      const res = await fetch(
        `${apiBaseUrl}/households/${selectedHousehold.id}/members/${memberId}`,
        { method: 'DELETE' }
      );
      if (!res.ok) {
        throw new Error('Failed to remove member');
      }
      await fetchHouseholds();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove member');
    }
  };

  const openMealEditor = (member: Member) => {
    const initialSelections = member.meals.length ? [...member.meals] : [...MEAL_SLOTS];
    const normalizedSchedule = ensureScheduleStructure(member.meal_schedule ?? null, initialSelections);
    setMealEditor({
      open: true,
      member,
      selections: initialSelections,
      advanced: Boolean(member.meal_schedule),
      schedule: normalizedSchedule,
      saving: false,
      error: null
    });
  };

  const closeMealEditor = () => {
    setMealEditor({
      open: false,
      member: null,
      selections: [...MEAL_SLOTS],
      advanced: false,
      schedule: buildScheduleFromMeals(MEAL_SLOTS),
      saving: false,
      error: null
    });
  };

  const toggleMealSelection = (meal: string) => {
    setMealEditor((state) => {
      if (state.advanced) {
        return state;
      }
      const exists = state.selections.includes(meal);
      const selections = exists
        ? state.selections.filter((item) => item !== meal)
        : [...state.selections, meal];
      return { ...state, selections, schedule: buildScheduleFromMeals(selections) };
    });
  };

  const toggleAdvancedSchedule = () => {
    setMealEditor((state) => {
      if (!state.member) {
        return state;
      }
      if (state.advanced) {
        return {
          ...state,
          advanced: false,
          schedule: buildScheduleFromMeals(state.selections)
        };
      }
      return {
        ...state,
        advanced: true,
        schedule: ensureScheduleStructure(state.schedule, state.selections)
      };
    });
  };

  const toggleScheduleSlot = (day: string, slot: string) => {
    setMealEditor((state) => {
      if (!state.advanced) {
        return state;
      }
      const schedule: MemberMealSchedule = { ...state.schedule };
      const daySchedule = { ...(schedule[day] ?? {}) };
      daySchedule[slot] = !daySchedule[slot];
      schedule[day] = daySchedule;
      const derivedMeals = deriveMealsFromSchedule(schedule);
      return {
        ...state,
        schedule,
        selections: derivedMeals.length ? derivedMeals : state.selections
      };
    });
  };

  const submitMealEditor = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedHousehold || !mealEditor.member) {
      return;
    }
    const derivedMeals = mealEditor.advanced
      ? deriveMealsFromSchedule(mealEditor.schedule)
      : mealEditor.selections;
    if (derivedMeals.length === 0) {
      setMealEditor((state) => ({
        ...state,
        error: 'Select at least one meal.'
      }));
      return;
    }
    setMealEditor((state) => ({ ...state, saving: true, error: null }));
    try {
      const res = await fetch(
        `${apiBaseUrl}/households/${selectedHousehold.id}/members/${mealEditor.member.id}/meals`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            meals: derivedMeals,
            schedule: mealEditor.advanced ? mealEditor.schedule : undefined
          })
        }
      );
      if (!res.ok) {
        throw new Error('Unable to update meals');
      }
      await fetchHouseholds();
      closeMealEditor();
    } catch (err) {
      setMealEditor((state) => ({
        ...state,
        error: err instanceof Error ? err.message : 'Unable to update meals',
        saving: false
      }));
    }
  };

  const handleCreateHousehold = async () => {
    if (!newHouseholdName.trim()) {
      return;
    }
    setCreatingHousehold(true);
    try {
      const res = await fetch(`${apiBaseUrl}/households`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newHouseholdName.trim() }),
      });
      if (!res.ok) {
        throw new Error('Failed to create household');
      }
      const created: Household = await res.json();
      setNewHouseholdName('');
      setSelectedHouseholdId(created.id);
      await fetchHouseholds();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create household');
    } finally {
      setCreatingHousehold(false);
    }
  };

  const updateKitchenToolQuantity = async (toolId: number, nextQuantity: number) => {
    if (!selectedHousehold) {
      return;
    }
    setKitchenBusy(true);
    try {
      const res = await fetch(
        `${apiBaseUrl}/households/${selectedHousehold.id}/kitchen/${toolId}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ quantity: Math.max(0, nextQuantity) })
        }
      );
      if (!res.ok) {
        throw new Error('Failed to update tool');
      }
      await fetchHouseholds();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update tool');
    } finally {
      setKitchenBusy(false);
    }
  };

  const adjustKitchenToolQuantity = (toolId: number, delta: number) => {
    const current = kitchenTools.find((tool) => tool.id === toolId)?.quantity ?? 0;
    updateKitchenToolQuantity(toolId, current + delta);
  };

  const handleDeleteKitchenTool = async (toolId: number) => {
    if (!selectedHousehold) {
      return;
    }
    setKitchenBusy(true);
    try {
      const res = await fetch(
        `${apiBaseUrl}/households/${selectedHousehold.id}/kitchen/${toolId}`,
        { method: 'DELETE' }
      );
      if (!res.ok) {
        throw new Error('Failed to delete tool');
      }
      await fetchHouseholds();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete tool');
    } finally {
      setKitchenBusy(false);
    }
  };

  const handleAddKitchenTool = async () => {
    if (!selectedHousehold || !toolLabel.trim()) {
      return;
    }
    setKitchenBusy(true);
    try {
      const res = await fetch(
        `${apiBaseUrl}/households/${selectedHousehold.id}/kitchen`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            label: toolLabel.trim(),
            category: toolCategory.trim() || undefined,
            quantity: Math.max(0, toolQuantity)
          })
        }
      );
      if (!res.ok) {
        throw new Error('Failed to add tool');
      }
      setToolLabel('');
      setToolCategory('');
      setToolQuantity(1);
      await fetchHouseholds();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add tool');
    } finally {
      setKitchenBusy(false);
    }
  };

  const sendAssistantMessage = useCallback(
    async (sessionId: string, message: string) => {
      if (!selectedHousehold) {
        return;
      }
      setAssistantBusy(true);
      if (message.trim()) {
        setAssistantMessages((prev) => [
          ...prev,
          { id: `user-${Date.now()}`, role: 'user', text: message }
        ]);
      }
      try {
        const res = await fetch(
          `${apiBaseUrl}/households/${selectedHousehold.id}/assistant`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              session_id: sessionId,
              message: message.trim() ? message : null
            })
          }
        );
        if (!res.ok) {
          throw new Error('Assistant is unavailable');
        }
        const data = await res.json();
        setAssistantStage(data.stage);
        setAssistantMessages((prev) => [
          ...prev,
          { id: `agent-${Date.now()}`, role: 'agent', text: data.agent_message }
        ]);
        if (data.completed) {
          setAssistantInput('');
          await fetchHouseholds();
        }
      } catch (err) {
        setAssistantMessages((prev) => [
          ...prev,
          {
            id: `agent-error-${Date.now()}`,
            role: 'agent',
            text:
              err instanceof Error
                ? err.message
                : 'Assistant encountered an error.'
          }
        ]);
      } finally {
        setAssistantBusy(false);
      }
    },
    [apiBaseUrl, fetchHouseholds, selectedHousehold]
  );

  const openAssistant = async () => {
    if (!selectedHousehold) {
      return;
    }
    const sessionId =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `assistant-${Date.now()}`;
    setAssistantSessionId(sessionId);
    setAssistantMessages([]);
    setAssistantInput('');
    setAssistantStage('ask_name');
    setAssistantOpen(true);
    await sendAssistantMessage(sessionId, '');
  };

  const closeAssistant = () => {
    setAssistantOpen(false);
    setAssistantSessionId(null);
    setAssistantMessages([]);
    setAssistantInput('');
    setAssistantStage('');
  };

  const showEmpty =
    !loading && selectedHousehold && selectedHousehold.members.length === 0;

  return (
    <>
      <div className="space-y-6 lg:grid lg:grid-cols-[1.5fr,1fr] lg:space-y-0 lg:gap-6">
        <div className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-400">
                Household
              </h2>
              <p className="mt-1 text-sm text-slate-300">
                Manage the people EcoFood plans for. Data is stored in the SQL database, so every change is saved.
              </p>
            </div>
            <div className="space-y-1 text-xs text-slate-400">
              <label className="text-[0.65rem] uppercase tracking-[0.2em]">
                Active household
              </label>
              <select
                value={selectedHouseholdId ?? ''}
                onChange={(e) => setSelectedHouseholdId(Number(e.target.value))}
                className="min-w-[200px] rounded-full border border-slate-700 bg-slate-950/80 px-3 py-1.5 text-slate-100"
              >
                {households.map((household) => (
                  <option key={household.id} value={household.id}>
                    {household.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {error && (
            <div className="rounded-2xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-xs text-rose-100">
              {error}
            </div>
          )}

          {loading && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 px-4 py-5 text-center text-sm text-slate-300">
              Loading household…
            </div>
          )}

          {showEmpty && (
            <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 px-4 py-6 text-center text-sm text-slate-400">
              No members yet. Use the form or the assistant to add your first profile.
            </div>
          )}

          <div className="grid gap-3 md:grid-cols-2">
            {selectedHousehold?.members.map((member) => (
              <article
                key={member.id}
                className="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-sm shadow-slate-950/80"
              >
                <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-cyan-400 via-sky-500 to-emerald-400 opacity-80" />
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-100">
                      {member.name}
                    </h3>
                    <p className="text-[0.7rem] uppercase tracking-[0.2em] text-slate-500">
                      {member.role}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => openMealEditor(member)}
                      className="rounded-full border border-slate-700/80 px-2 py-0.5 text-[0.65rem] text-cyan-200 hover:border-cyan-400 hover:text-cyan-100"
                    >
                      Meals
                    </button>
                    <button
                      onClick={() => handleRemoveMember(member.id)}
                      className="rounded-full border border-slate-700/80 px-2 py-0.5 text-[0.65rem] text-slate-300 hover:border-rose-400 hover:text-rose-100"
                    >
                      Remove
                    </button>
                  </div>
                </div>

                {member.allergens.length > 0 && (
                  <div className="mt-3">
                    <p className="text-[0.65rem] font-medium uppercase tracking-[0.18em] text-slate-500">
                      Allergens
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {member.allergens.map((label) => (
                        <span
                          key={label}
                          className="rounded-full bg-rose-500/10 px-2 py-0.5 text-[0.65rem] text-rose-200"
                        >
                          {label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {member.likes.length > 0 && (
                  <div className="mt-3">
                    <p className="text-[0.65rem] font-medium uppercase tracking-[0.18em] text-slate-500">
                      Preferences
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {member.likes.map((label) => (
                        <span
                          key={label}
                          className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[0.65rem] text-emerald-200"
                        >
                          {label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mt-3">
                  <p className="text-[0.65rem] font-medium uppercase tracking-[0.18em] text-slate-500">
                    Eats
                  </p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {member.meals.length ? (
                      member.meals.map((meal) => (
                        <span
                          key={meal}
                          className="rounded-full border border-cyan-400/40 bg-cyan-500/10 px-2 py-0.5 text-[0.65rem] text-cyan-100"
                        >
                          {meal}
                        </span>
                      ))
                    ) : (
                      <span className="text-[0.65rem] text-slate-500">
                        No meals selected
                      </span>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/80 p-4">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
              Add household member
            </h3>
            <p className="text-[0.7rem] text-slate-500">Saved directly to the database.</p>
          </div>
*** End Patch

          <div className="space-y-3 text-xs md:text-sm">
            <div className="space-y-1">
              <label className="text-[0.7rem] font-medium uppercase tracking-[0.18em] text-slate-500">
                Name
              </label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Alex"
                className="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none ring-cyan-400/60 ring-offset-0 focus:border-cyan-400 focus:ring-1"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[0.7rem] font-medium uppercase tracking-[0.18em] text-slate-500">
                Role
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400"
              >
                <option value="Adult">Adult</option>
                <option value="Child">Child</option>
                <option value="Guest">Guest</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[0.7rem] font-medium uppercase tracking-[0.18em] text-slate-500">
                Allergens (comma separated)
              </label>
              <input
                value={allergensInput}
                onChange={(e) => setAllergensInput(e.target.value)}
                placeholder="e.g. peanuts, lactose"
                className="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[0.7rem] font-medium uppercase tracking-[0.18em] text-slate-500">
                Preferences (comma separated)
              </label>
              <input
                value={likesInput}
                onChange={(e) => setLikesInput(e.target.value)}
                placeholder="e.g. Mediterranean, spicy"
                className="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400"
              />
            </div>

            <button
              onClick={handleAddMember}
              disabled={!selectedHousehold || !name.trim()}
              className="mt-2 inline-flex w-full items-center justify-center rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-400 px-4 py-2 text-sm font-semibold text-slate-950 shadow-[0_0_18px_rgba(34,211,238,0.7)] hover:from-cyan-400 hover:to-emerald-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Save member
            </button>
            <p className="text-[0.65rem] text-slate-500">
              {householdSummary.total} member
              {householdSummary.total === 1 ? '' : 's'} tracked · Allergens:
              {householdSummary.allergens.length
                ? ` ${householdSummary.allergens.join(', ')}`
                : ' none yet'}
            </p>
          </div>

        </div>

        <div className="space-y-4">
          <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-sm text-slate-200">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
                Household actions
              </h3>
              <p className="text-[0.75rem] text-slate-400">
                Create new households or launch the guided assistant to capture members faster.
              </p>
            </div>
            <div className="space-y-2">
              <label className="text-[0.65rem] uppercase tracking-[0.2em] text-slate-500">
                New household
              </label>
              <div className="flex flex-col gap-2 sm:flex-row">
                <input
                  value={newHouseholdName}
                  onChange={(event) => setNewHouseholdName(event.target.value)}
                  placeholder="e.g. Rooftop coop"
                  className="flex-1 rounded-full border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400"
                />
                <button
                  onClick={handleCreateHousehold}
                  disabled={!newHouseholdName.trim() || creatingHousehold}
                  className="rounded-full border border-emerald-400/50 px-4 py-2 text-xs font-semibold text-emerald-100 hover:bg-emerald-500/10 disabled:opacity-40"
                >
                  {creatingHousehold ? 'Creating…' : 'Create'}
                </button>
              </div>
              <p className="text-[0.65rem] text-slate-500">
                Switch between households using the selector above to customize each crew.
              </p>
            </div>
            <button
              onClick={openAssistant}
              disabled={!selectedHousehold}
              className="w-full rounded-2xl border border-cyan-500/40 px-4 py-2 text-xs font-semibold text-cyan-100 hover:border-cyan-400 disabled:opacity-50"
            >
              Launch household assistant
            </button>
          </div>

          <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-400">
                  Kitchen setup
                </h3>
                <p className="text-sm text-slate-300">
                  Quantities help the agents choose recipes that match {selectedHousehold?.name ?? 'this household'}'s cookware.
                </p>
              </div>
              {kitchenBusy && <p className="text-xs text-cyan-200">Updating inventory…</p>}
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              {kitchenTools.map((tool) => (
                <div
                  key={tool.id}
                  className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3 text-sm text-slate-100"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-slate-50">{tool.label}</p>
                      <p className="text-[0.65rem] uppercase tracking-[0.2em] text-slate-500">
                        {tool.category || 'Custom'}
                      </p>
                    </div>
                    <button
                      onClick={() => handleDeleteKitchenTool(tool.id)}
                      className="rounded-full border border-slate-700/70 px-2 py-0.5 text-[0.65rem] text-slate-300 hover:border-rose-400 hover:text-rose-100"
                    >
                      Remove
                    </button>
                  </div>
                  <div className="mt-3 flex items-center gap-2 text-xs">
                    <button
                      onClick={() => adjustKitchenToolQuantity(tool.id, -1)}
                      disabled={kitchenBusy || tool.quantity <= 0}
                      className="h-8 w-8 rounded-full border border-slate-700 text-base text-slate-200 hover:border-cyan-400 disabled:opacity-40"
                    >
                      –
                    </button>
                    <span className="min-w-[48px] text-center text-lg font-semibold text-slate-50">
                      {tool.quantity}
                    </span>
                    <button
                      onClick={() => adjustKitchenToolQuantity(tool.id, 1)}
                      disabled={kitchenBusy}
                      className="h-8 w-8 rounded-full border border-slate-700 text-base text-slate-200 hover:border-cyan-400 disabled:opacity-40"
                    >
                      +
                    </button>
                  </div>
                </div>
              ))}
              {!kitchenTools.length && (
                <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/50 p-4 text-sm text-slate-400">
                  No tools recorded yet. Add cookware to tailor recipe suggestions.
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-100">
              <h4 className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-400">
                Add a kitchen tool
              </h4>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <div className="space-y-1">
                  <label className="text-[0.65rem] uppercase tracking-[0.2em] text-slate-500">
                    Label
                  </label>
                  <input
                    value={toolLabel}
                    onChange={(event) => setToolLabel(event.target.value)}
                    placeholder="e.g. Dutch oven"
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[0.65rem] uppercase tracking-[0.2em] text-slate-500">
                    Category (optional)
                  </label>
                  <input
                    value={toolCategory}
                    onChange={(event) => setToolCategory(event.target.value)}
                    placeholder="Pan, bakeware…"
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[0.65rem] uppercase tracking-[0.2em] text-slate-500">
                    Quantity
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={toolQuantity}
                    onChange={(event) =>
                      setToolQuantity(Math.max(0, Number(event.target.value) || 0))
                    }
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400"
                  />
                </div>
              </div>
              <button
                onClick={handleAddKitchenTool}
                disabled={!toolLabel.trim() || kitchenBusy}
                className="mt-3 inline-flex w-full items-center justify-center rounded-xl border border-cyan-400/60 bg-cyan-500/10 px-4 py-2 text-sm font-semibold text-cyan-100 hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Add tool
              </button>
              <p className="mt-2 text-xs text-slate-500">
                Defaults include pans, casseroles, and bakeware. Add any specialty gear you rely on.
              </p>
            </div>
          </div>
        </div>
      </div>

      {assistantOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/80 px-4 py-6">
          <div className="relative w-full max-w-lg rounded-3xl border border-slate-700 bg-slate-900/95 p-5 text-sm text-slate-100 shadow-[0_0_45px_rgba(15,118,255,0.25)]">
            <button
              onClick={closeAssistant}
              className="absolute right-4 top-4 rounded-full border border-slate-700/60 px-2 py-0.5 text-[0.65rem] text-slate-300 hover:border-rose-400 hover:text-rose-100"
            >
              Close
            </button>
            <h4 className="text-xs font-semibold uppercase tracking-[0.25em] text-cyan-200">
              Household assistant
            </h4>
            <p className="mt-1 text-[0.7rem] text-slate-400">Stage: {assistantStage || 'initializing'}</p>

            <div className="mt-4 h-64 space-y-3 overflow-y-auto rounded-2xl border border-slate-800/60 bg-slate-950/80 p-3">
              {assistantMessages.length === 0 && (
                <p className="text-xs text-slate-500">Connecting to the assistant…</p>
              )}
              {assistantMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === 'agent' ? 'justify-start' : 'justify-end'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-3 py-2 text-[0.75rem] ${
                      msg.role === 'agent'
                        ? 'bg-slate-800/80 text-slate-100'
                        : 'bg-cyan-500/20 text-cyan-100'
                    }`}
                  >
                    {msg.text}
                  </div>
                </div>
              ))}
            </div>

            <form
              className="mt-4 flex gap-2"
              onSubmit={async (event) => {
                event.preventDefault();
                if (!assistantSessionId || !assistantInput.trim()) {
                  return;
                }
                await sendAssistantMessage(assistantSessionId, assistantInput);
                setAssistantInput('');
              }}
            >
              <input
                value={assistantInput}
                onChange={(event) => setAssistantInput(event.target.value)}
                placeholder="Type your reply..."
                className="flex-1 rounded-2xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400"
              />
              <button
                type="submit"
                disabled={!assistantSessionId || !assistantInput.trim() || assistantBusy}
                className="rounded-2xl bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50"
              >
                Send
              </button>
            </form>
          </div>
        </div>
      )}

      {mealEditor.open && mealEditor.member && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/80 px-4 py-6">
          <div className="w-full max-w-lg rounded-3xl border border-slate-800 bg-slate-950/90 p-5 text-sm text-slate-100 shadow-[0_0_45px_rgba(34,211,238,0.25)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Member meals</p>
                <h4 className="text-lg font-semibold text-slate-50">
                  {mealEditor.member.name}
                </h4>
              </div>
              <button
                onClick={closeMealEditor}
                className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-cyan-400 hover:text-cyan-100"
              >
                Close
              </button>
            </div>
            <form className="mt-4 space-y-4" onSubmit={submitMealEditor}>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-slate-400">
                  {mealEditor.advanced
                    ? 'Toggle specific days/slots below.'
                    : 'Select the meals this member usually sits for.'}
                </p>
                <button
                  type="button"
                  onClick={toggleAdvancedSchedule}
                  className="text-xs text-cyan-200 underline-offset-4 hover:underline"
                >
                  {mealEditor.advanced ? 'Switch to simple mode' : 'Advanced per-day schedule'}
                </button>
              </div>
              {!mealEditor.advanced && (
                <div className="flex flex-wrap gap-2">
                  {MEAL_SLOTS.map((slot) => {
                    const active = mealEditor.selections.includes(slot);
                    return (
                      <button
                        type="button"
                        key={slot}
                        onClick={() => toggleMealSelection(slot)}
                        className={`rounded-full border px-4 py-1 text-sm transition ${
                          active
                            ? 'border-cyan-400/70 bg-cyan-500/10 text-cyan-100 shadow-[0_0_20px_rgba(34,211,238,0.25)]'
                            : 'border-slate-700 bg-slate-900/60 text-slate-300 hover:border-cyan-400/40 hover:text-cyan-100'
                        }`}
                      >
                        {slot}
                      </button>
                    );
                  })}
                </div>
              )}
              {mealEditor.advanced && (
                <div className="space-y-2 text-[0.7rem]">
                  {CALENDAR_DAYS.map((day) => (
                    <div
                      key={day}
                      className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3"
                    >
                      <p className="text-[0.65rem] font-semibold uppercase tracking-[0.25em] text-slate-400">
                        {day}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {MEAL_SLOTS.map((slot) => {
                          const active = mealEditor.schedule[day]?.[slot];
                          return (
                            <button
                              type="button"
                              key={`${day}-${slot}`}
                              onClick={() => toggleScheduleSlot(day, slot)}
                              className={`rounded-full border px-3 py-1 text-[0.65rem] ${
                                active
                                  ? 'border-emerald-400/60 bg-emerald-500/10 text-emerald-100'
                                  : 'border-slate-700 bg-slate-950/60 text-slate-400 hover:border-cyan-400/40 hover:text-cyan-100'
                              }`}
                            >
                              {slot}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {mealEditor.error && (
                <div className="rounded-2xl border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-100">
                  {mealEditor.error}
                </div>
              )}
              <button
                type="submit"
                disabled={mealEditor.saving}
                className="w-full rounded-2xl bg-gradient-to-r from-cyan-500 to-emerald-400 px-4 py-2 text-center text-sm font-semibold text-slate-950 shadow-[0_0_30px_rgba(34,211,238,0.45)] disabled:opacity-50"
              >
                {mealEditor.saving ? 'Saving…' : 'Save meals'}
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

type SettingsTabProps = {
  apiBaseUrl: string;
};

function SettingsTab({ apiBaseUrl }: SettingsTabProps) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const callAdminEndpoint = async (path: string, label: string) => {
    setBusy(true);
    setMessage(`Calling ${label}…`);
    try {
      const res = await fetch(`${apiBaseUrl}${path}`, {
        method: 'POST'
      });
      const data = await res.json().catch(() => ({}));
      setMessage(
        `Backend responded (${res.status}): ${
          data.status || 'see logs / implementation'
        }`
      );
    } catch (err) {
      setMessage(
        `Failed to reach backend at ${apiBaseUrl}${path}. Is docker-compose running?`
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid gap-6 md:grid-cols-[1.3fr,1fr]">
      <div className="space-y-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-[0.25em] text-slate-400">
            Developer settings
          </h2>
          <p className="mt-1 text-sm text-slate-300">
            Tools to reset or recreate database structures while iterating on
            the schema. For now, the backend endpoints are stubs; later they
            will perform real migrations and truncations.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.22em] text-rose-300">
              Global reset
            </h3>
            <p className="text-xs text-slate-300">
              Drop and recreate all core tables. Use this when you change the
              schema and want a clean slate during development.
            </p>
            <button
              onClick={() =>
                callAdminEndpoint('/admin/reset-db', 'reset database')
              }
              disabled={busy}
              className="inline-flex w-full items-center justify-center rounded-xl border border-rose-400/60 bg-rose-500/10 px-3 py-2 text-xs font-semibold text-rose-100 shadow-[0_0_18px_rgba(248,113,113,0.4)] hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Reset entire database (DEV)
            </button>
          </div>

          <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.22em] text-sky-300">
              Table-level tools
            </h3>
            <p className="text-xs text-slate-300">
              Recreate a single table to debug issues without losing everything.
              This will later accept table names like{' '}
              <code className="rounded bg-slate-950/80 px-1 py-0.5">
                households
              </code>{' '}
              or{' '}
              <code className="rounded bg-slate-950/80 px-1 py-0.5">
                pantry_items
              </code>
              .
            </p>
            <button
              onClick={() =>
                callAdminEndpoint(
                  '/admin/reset-table/households',
                  'reset households table'
                )
              }
              disabled={busy}
              className="inline-flex w-full items-center justify-center rounded-xl border border-sky-400/60 bg-sky-500/10 px-3 py-2 text-xs font-semibold text-sky-100 hover:bg-sky-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Reset households table (stub)
            </button>
            <button
              onClick={() =>
                callAdminEndpoint(
                  '/admin/reset-table/meal_plans',
                  'reset meal_plans table'
                )
              }
              disabled={busy}
              className="inline-flex w-full items-center justify-center rounded-xl border border-emerald-400/60 bg-emerald-500/10 px-3 py-2 text-xs font-semibold text-emerald-100 hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Reset meal_plans table (stub)
            </button>
          </div>
        </div>
      </div>

      <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-xs text-slate-300">
        <h3 className="text-[0.7rem] font-semibold uppercase tracking-[0.22em] text-slate-400">
          Status & wiring
        </h3>
        <p>
          The buttons on this screen call FastAPI admin endpoints exposed by the
          backend service ({apiBaseUrl}). Currently they return stub responses
          so you can verify connectivity via Docker before wiring real DB
          operations.
        </p>
        <p className="text-[0.7rem] text-slate-500">
          Later, these endpoints will:
        </p>
        <ul className="list-disc space-y-1 pl-4 text-[0.7rem] text-slate-400">
          <li>Run safe migrations and truncations per table.</li>
          <li>Log each destructive action with who/when metadata.</li>
          <li>Optionally seed demo data for faster testing.</li>
        </ul>
        {message && (
          <div className="mt-3 rounded-xl border border-slate-700 bg-slate-950/80 p-3 text-[0.7rem] text-slate-100">
            {message}
          </div>
        )}
      </div>
    </div>
  );
}
