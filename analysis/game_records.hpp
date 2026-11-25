// Included inside namespace staxxit, after Config. Optional bounded archive.
struct RecordTotals {
  std::array<std::array<int, 2>, 2> scores{};
  std::array<int, 2> controlled{}, active{};
};
RecordTotals record_totals(const State& s) {
  RecordTotals t;
  for (int p = 0; p < N; ++p) {
    const auto& stack = s.b[p];
    if (!stack.h) continue;
    int owner = stack.owner();
    if (geo.outer[p] >= 0) {
      ++t.scores[owner][0];
      t.scores[owner][1] += stack.h;
    } else {
      ++t.active[owner];
      t.controlled[owner] += stack.h;
    }
  }
  return t;
}
struct RecordMove {
  Move move;
  int side = 0, legal_count = 0, source_height = 0, target_height = 0;
  int placement_strategy = -1;
};
struct RecordOffer { int ply = -1, offered_height = 0, attacker_height = 0; };
struct RecordComeback { int ply = -1, field_deficit = 0, stone_deficit = 0; };
struct RecordMaterial { int ply = -1, deficit = 0; };
struct GameRecord {
  uint64_t id = 0;
  int outcome = 5, captures = 0, max_height = 0;
  std::vector<RecordMove> moves;
  RecordTotals final;
  std::array<RecordOffer, 2> offers{};
  std::array<RecordComeback, 2> comeback_score{};
  std::array<RecordMaterial, 2> comeback_material{};
  void append(const State& before, Move move, int legal_count, int strategy) {
    RecordMove item{move, before.side, legal_count,
      move.p < 0 ? (move.t == 'p' ? 1 : 0) : int(before.b[move.p].h),
      move.q < 0 ? 0 : int(before.b[move.q].h),
      move.t == 'p' ? strategy : -1};
    moves.push_back(item);
    captures += move.t == 'c';
    if (moves.size() < 3) return;
    size_t i = moves.size() - 3;
    const auto &a = moves[i], &b = moves[i + 1], &c = moves[i + 2];
    if ((a.move.t != 'p' && a.move.t != 'm') ||
        b.move.t != 'c' || c.move.t != 'c' || a.side != c.side ||
        a.side == b.side || a.move.q != b.move.q || a.move.q != c.move.q)
      return;
    auto& best = offers[a.side];
    if (best.ply < 0 || std::make_pair(b.source_height, a.source_height) >
        std::make_pair(best.attacker_height, best.offered_height))
      best = {int(i + 1), a.source_height, b.source_height};
  }
  void observe(const State& after, bool terminal) {
    if (terminal || after.res[0] || after.res[1]) return;
    auto t = record_totals(after);
    for (int c = 0; c < 2; ++c) {
      int opponent = 1 - c;
      if (t.scores[c] < t.scores[opponent]) {
        int fields = t.scores[opponent][0] - t.scores[c][0];
        int stones = t.scores[opponent][1] - t.scores[c][1];
        auto& best = comeback_score[c];
        if (best.ply < 0 || std::make_pair(fields, stones) >
            std::make_pair(best.field_deficit, best.stone_deficit))
          best = {int(moves.size()), fields, stones};
      }
      int deficit = t.controlled[opponent] - t.controlled[c];
      if (t.scores[c] == t.scores[opponent] && deficit >= 6) {
        auto& best = comeback_material[c];
        if (best.ply < 0 || deficit > best.deficit)
          best = {int(moves.size()), deficit};
      }
    }
  }
};
struct RecordSelection {
  bool present = false;
  std::string category;
  int player = -1, strategy = -1;
  std::vector<int> rank;
  GameRecord game;
};
struct RecordStore {
  std::array<RecordSelection, 20> slots;
  void retain(int slot, const char* category, int player, int strategy,
              const std::vector<int>& rank, const GameRecord& game) {
    auto& current = slots[slot];
    if (!current.present || rank > current.rank ||
        (rank == current.rank && game.id < current.game.id))
      current = {true, category, player, strategy, rank, game};
  }
  void consider(const Config& cfg, const GameRecord& g) {
    int turns = int(g.moves.size());
    bool won = g.outcome == 0 || g.outcome == 1;
    retain(1, "longest_observed", -1, -1, {turns}, g);
    retain(3, "most_captures", -1, -1, {g.captures}, g);
    retain(4, "tallest_stack", -1, -1, {g.max_height}, g);
    if (g.outcome <= 2) retain(2, "longest_regular", -1, -1, {turns}, g);
    if (!won) return;
    int winner = g.outcome, opponent = 1 - winner;
    retain(0, "shortest_won", winner, -1, {-turns}, g);
    bool fixed = true;
    for (int x : cfg.schedule[winner]) if (x >= 0) fixed = false;
    if (fixed) {
      int strategy = cfg.strategy[winner];
      retain(8 + strategy, "best_strategy", winner, strategy,
             {g.final.scores[winner][0] - g.final.scores[opponent][0],
              g.final.scores[winner][1] - g.final.scores[opponent][1], -turns}, g);
    }
    const auto& offer = g.offers[winner];
    if (offer.ply >= 0)
      retain(5, "tactical_offer", winner, -1,
             {offer.attacker_height, offer.offered_height}, g);
    const auto& score = g.comeback_score[winner];
    if (score.ply >= 0)
      retain(6, "comeback_score", winner, -1,
             {score.field_deficit, score.stone_deficit, -score.ply}, g);
    const auto& material = g.comeback_material[winner];
    if (material.ply >= 0)
      retain(7, "comeback_material", winner, -1,
             {material.deficit, -material.ply}, g);
  }
  void add(const RecordStore& other) {
    for (size_t i = 0; i < slots.size(); ++i) {
      const auto& entry = other.slots[i];
      if (entry.present)
        retain(int(i), entry.category.c_str(), entry.player, entry.strategy,
               entry.rank, entry.game);
    }
  }
};

template <class C>
void record_array(std::ostream& o, const C& a) {
  o << '[';
  bool comma = false;
  for (auto value : a) {
    if (comma) o << ',';
    comma = true;
    o << value;
  }
  o << ']';
}
void record_scores(std::ostream& o, const RecordTotals& t) {
  o << '[';
  record_array(o, t.scores[0]);
  o << ',';
  record_array(o, t.scores[1]);
  o << ']';
}
void record_config(std::ostream& o, const Config& c) {
  o << "{\"variant\":\"" << (c.variant ? 'B' : 'A')
    << "\",\"seed\":\"" << c.seed << "\",\"start\":" << c.start
    << ",\"games\":" << c.games << ",\"limit\":" << c.limit
    << ",\"white\":" << c.strategy[0] << ",\"black\":" << c.strategy[1]
    << ",\"white_policy\":" << c.policy[0] << ",\"black_policy\":" << c.policy[1]
    << ",\"white_escape_first\":" << (c.escape_first[0] ? "true" : "false")
    << ",\"black_escape_first\":" << (c.escape_first[1] ? "true" : "false")
    << ",\"white_schedule\":";
  record_array(o, c.schedule[0]);
  o << ",\"black_schedule\":";
  record_array(o, c.schedule[1]);
  o << '}';
}
void record_snapshot(std::ostream& o, const State& s, int ply) {
  auto totals = record_totals(s);
  o << "{\"ply\":" << ply << ",\"side\":" << s.side
    << ",\"reserve\":[" << s.res[0] << ',' << s.res[1]
    << "],\"passes\":" << s.passes << ",\"stacks\":[";
  for (int p = 0; p < N; ++p) {
    if (p) o << ',';
    o << '"';
    if (!s.b[p].h) o << '-';
    else for (int j = 0; j < s.b[p].h; ++j) o << ((s.b[p].bits >> j) & 1);
    o << '"';
  }
  o << "],\"scores\":";
  record_scores(o, totals);
  o << ",\"controlled\":";
  record_array(o, totals.controlled);
  o << ",\"active_stacks\":";
  record_array(o, totals.active);
  o << '}';
}
const char* record_reason(int outcome) {
  const char* names[] = {"white", "black", "draw", "repeat", "blocked", "limit"};
  return names[outcome];
}
void record_trace(std::ostream& o, const Config& cfg, const GameRecord& g) {
  o << "{\"schema\":\"staxxit.trace.v1\",\"config\":";
  record_config(o, cfg);
  o << ",\"game_id\":" << g.id << ",\"initial_rng_state\":\""
    << mix(cfg.seed ^ mix(g.id)) << "\",\"outcome\":" << g.outcome
    << ",\"termination\":\"" << record_reason(g.outcome)
    << "\",\"regular\":" << (g.outcome <= 2 ? "true" : "false")
    << ",\"censored\":" << (g.outcome >= 3 ? "true" : "false")
    << ",\"metrics\":{\"turns\":" << g.moves.size()
    << ",\"captures\":" << g.captures << ",\"max_height\":" << g.max_height
    << ",\"final_scores\":";
  record_scores(o, g.final);
  o << ",\"offers\":[";
  for (int c = 0; c < 2; ++c) {
    if (c) o << ',';
    const auto& offer = g.offers[c];
    if (offer.ply < 0) o << "null";
    else o << "{\"ply\":" << offer.ply << ",\"offered_height\":"
           << offer.offered_height << ",\"attacker_height\":" << offer.attacker_height << '}';
  }
  o << "],\"comeback_score\":[";
  for (int c = 0; c < 2; ++c) {
    if (c) o << ',';
    const auto& score = g.comeback_score[c];
    if (score.ply < 0) o << "null";
    else o << "{\"ply\":" << score.ply << ",\"field_deficit\":"
           << score.field_deficit << ",\"stone_deficit\":" << score.stone_deficit << '}';
  }
  o << "],\"comeback_material\":[";
  for (int c = 0; c < 2; ++c) {
    if (c) o << ',';
    const auto& material = g.comeback_material[c];
    if (material.ply < 0) o << "null";
    else o << "{\"ply\":" << material.ply << ",\"deficit\":" << material.deficit << '}';
  }
  o << "]},\"moves\":[";
  for (size_t i = 0; i < g.moves.size(); ++i) {
    if (i) o << ',';
    const auto& p = g.moves[i];
    o << "{\"ply\":" << i + 1 << ",\"side\":" << p.side
      << ",\"t\":\"" << p.move.t << "\",\"p\":" << p.move.p
      << ",\"q\":" << p.move.q << ",\"k\":" << p.move.k
      << ",\"legal_count\":" << p.legal_count << ",\"source_height\":"
      << p.source_height << ",\"target_height\":" << p.target_height
      << ",\"placement_strategy\":" << p.placement_strategy << '}';
  }
  o << "],\"snapshots\":[";
  State s;
  record_snapshot(o, s, 0);
  for (size_t i = 0; i < g.moves.size(); ++i) {
    const auto& p = g.moves[i];
    if (s.side != p.side) throw std::runtime_error("archive replay side mismatch");
    if (p.move.t == 'x') ++s.passes;
    else { s.passes = 0; step(s, p.move); }
    conservation(s);
    s.side = 1 - s.side;
    o << ',';
    record_snapshot(o, s, int(i + 1));
  }
  o << "]}";
}
void record_catalog(std::ostream& o, const Config& cfg, const RecordStore& store) {
  o << "{\"schema\":\"staxxit.records.v1\",\"config\":";
  record_config(o, cfg);
  o << ",\"selections\":[";
  bool comma = false;
  std::vector<const GameRecord*> games;
  for (const auto& entry : store.slots) {
    if (!entry.present) continue;
    if (comma) o << ',';
    comma = true;
    o << "{\"category\":\"" << entry.category << "\",\"player\":" << entry.player
      << ",\"strategy\":" << entry.strategy << ",\"rank\":";
    record_array(o, entry.rank);
    o << ",\"game_id\":" << entry.game.id << '}';
    bool found = false;
    for (const auto* game : games) if (game->id == entry.game.id) found = true;
    if (!found) games.push_back(&entry.game);
  }
  o << "],\"games\":[";
  for (size_t i = 0; i < games.size(); ++i) {
    if (i) o << ',';
    record_trace(o, cfg, *games[i]);
  }
  o << "]}\n";
}
