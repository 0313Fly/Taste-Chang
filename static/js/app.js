const { createApp, computed, onMounted, ref } = Vue;

createApp({
  delimiters: ["[[", "]]"],
  setup() {
    const title = ref("常州美食排行榜");
    const query = ref("");
    const items = ref([]);
    const loading = ref(true);
    const error = ref("");

    const rankedItems = computed(() =>
      items.value.map((item, index) => ({
        ...item,
        medal: { 1: "🥇", 2: "🥈", 3: "🥉" }[index + 1] || String(index + 1),
      }))
    );

    async function fetchList() {
      loading.value = true;
      error.value = "";
      const params = new URLSearchParams();
      const q = query.value.trim();
      if (q) params.set("q", q);
      const url = params.size ? `/api/restaurants?${params}` : "/api/restaurants";
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`请求失败：${res.status}`);
        const data = await res.json();
        title.value = data.title || title.value;
        items.value = data.items || [];
      } catch (err) {
        error.value = err.message || "加载失败";
        items.value = [];
      } finally {
        loading.value = false;
      }
    }

    function onSearch() {
      fetchList();
    }

    onMounted(fetchList);

    return { title, query, items, loading, error, rankedItems, onSearch };
  },
}).mount("#app");
