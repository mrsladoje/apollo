import sqlite3
import json

def validate():
    conn = sqlite3.connect("historian.db")
    conn.row_factory = sqlite3.Row
    
    print("Validating Historian Data Invariants...")

    # 1. Basic Ranges
    res = conn.execute("SELECT min(health), max(health) FROM component_states").fetchone()
    print(f"  - Health Range: [{res[0]:.4f}, {res[1]:.4f}] (Expected [0, 1])")
    if not (0 <= res[0] <= 1 and 0 <= res[1] <= 1):
        print("    [FAIL] Health out of bounds!")

    # 2. Status Consistency (PLAN-A §6.4)
    res = conn.execute("""
        SELECT count(*) FROM component_states 
        WHERE (health < 0.1 AND status != 'FAILED') 
           OR (health >= 0.7 AND status != 'FUNCTIONAL')
    """).fetchone()
    print(f"  - Status Inconsistencies: {res[0]} (Expected 0)")

    # 3. Policy Performance Comparison (FR-2.4)
    print("  - Policy Performance (Average Health):")
    res = conn.execute("""
        SELECT policy, avg(health) as avg_h 
        FROM runs JOIN component_states USING (run_id) 
        GROUP BY policy 
        ORDER BY avg_h DESC
    """).fetchall()
    for row in res:
        print(f"    * {row['policy']:<6}: {row['avg_h']:.4f}")
    
    # Assert AI > NONE
    policies = {r['policy']: r['avg_h'] for r in res}
    if policies.get('ai', 0) > policies.get('none', 0):
        print("    [PASS] AI policy outperforms Dark Twin as expected.")
    else:
        print("    [FAIL] AI policy underperforming!")

    # 4. Failure Count Comparison
    print("  - Total Failures by Policy:")
    res = conn.execute("""
        SELECT policy, count(*) as fail_count 
        FROM runs JOIN component_states USING (run_id) 
        WHERE status = 'FAILED' 
        GROUP BY policy
    """).fetchall()
    for row in res:
        print(f"    * {row['policy']:<6}: {row['fail_count']} failed ticks")

    # 5. Decay Invariant (Sanity check on a single run)
    print("  - Testing Decay (stresed-none-seed0042, nozzle):")
    rows = conn.execute("""
        SELECT health FROM component_states 
        WHERE run_id = 'stressed-none-seed0042' AND component_id = 'nozzle' 
        ORDER BY t ASC
    """).fetchall()
    healths = [r['health'] for r in rows]
    is_monotone = all(healths[i] >= healths[i+1] for i in range(len(healths)-1))
    if is_monotone:
        print("    [PASS] Health is monotonically decreasing in NONE run.")
    else:
        # Check if there were any jumps
        jumps = [healths[i+1] - healths[i] for i in range(len(healths)-1) if healths[i+1] > healths[i]]
        if jumps:
            print(f"    [FAIL] Unexpected health increase in NONE run! Max jump: {max(jumps):.4f}")
        else:
            print("    [PASS] Health is stable or decreasing.")

    conn.close()

if __name__ == "__main__":
    validate()
