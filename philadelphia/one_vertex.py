import sys
import time
from pysat.solvers import Solver
from pysat.card import CardEnc
import random


def read_dataset(file_path):
    num_cells = 0
    demand_vector = [0]  # Thêm 0 ở đầu để index bắt đầu từ 1
    matrix = []
    
    with open(file_path, 'r') as file:
        # Đọc tất cả các dòng, loại bỏ khoảng trắng dư thừa và dòng trống
        lines = [line.strip() for line in file if line.strip()]
        
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Đọc số lượng cells
        if line.startswith("Number of cells:"):
            num_cells = int(line.split(":")[1].strip())
            
            # Khởi tạo ma trận với dòng index 0 rỗng (toàn số 0)
            matrix.append([0] * (num_cells + 1))
            
        # Đọc Demand Vector
        elif line.startswith("Demand Vector:"):
            i += 1  # Chuyển sang dòng chứa dữ liệu
            demands = list(map(int, lines[i].split(',')))
            demand_vector.extend(demands)
            
        # Đọc Matrix
        elif line.startswith("Matrix for"):
            i += 1  # Chuyển sang dòng chứa dòng đầu tiên của ma trận
            for _ in range(num_cells):
                if i < len(lines):
                    row_data = list(map(int, lines[i].split(',')))
                    # Thêm 0 ở đầu mỗi dòng để cột cũng có index bắt đầu từ 1
                    matrix.append([0] + row_data)
                    i += 1
            break  # Hoàn thành đọc ma trận
            
        i += 1

    return num_cells, demand_vector, matrix


def create_frequency_var(num_cells, UB):
    x = [[0] * (UB + 1) for _ in range(num_cells + 1)]
    top = 0
    for i in range(1, num_cells + 1):
        for j in range(1, UB + 1):
            top += 1
            x[i][j] = top
            
    return x, top

def add_exactly_k_constraints(solver, num_cells, UB, x, demand_vector, top):
    for i in range(1, num_cells + 1):
        vars_for_cell = [x[i][j] for j in range(1, UB + 1)]
        k = demand_vector[i]
        if k > 0:
            # Thêm ràng buộc Exactly k
            enc = CardEnc.equals(lits=vars_for_cell, bound=k, top_id=top, encoding=8)
            for clause in enc.clauses:
                solver.add_clause(clause)
            if enc.clauses:
                top = max(top, enc.nv)

def add_exactly_k_nsc(solver, num_cells, num_frequency, x, demand_vector, top):
    for l in range(1, num_cells + 1):
        K = demand_vector[l]
        r = [[0] * (K + 1) for _ in range(num_frequency + 1)]

        for i in range(1, K):
            for j in range(1, i + 1):
                top += 1
                r[i][j] = top
        for i in range(K, num_frequency + 1):
            for j in range(1, K + 1):
                top += 1
                r[i][j] = top

        # (1)  ¬x_i ∨ r(i,1)
        for i in range(1, num_frequency + 1):
            solver.add_clause([-x[l][i], r[i][1]])

        # (2)  ¬r(i-1,j) ∨ r(i,j)
        for i in range(2, num_frequency + 1):
            for j in range(1, min(i - 1, K) + 1):
                solver.add_clause([-r[i - 1][j], r[i][j]])

        # (3)  ¬x_i ∨ ¬r(i-1,j-1) ∨ r(i,j)
        for i in range(2, num_frequency + 1):
            for j in range(2, min(i, K) + 1):
                solver.add_clause([-x[l][i], -r[i - 1][j - 1], r[i][j]])

        # (4)  x_i ∨ ¬r(i,i)
        for i in range(1, K + 1):
            solver.add_clause([x[l][i], -r[i][i]])

        # (5)  r(i-1,j-1) ∨ ¬r(i,j)
        for i in range(2, num_frequency + 1):
            for j in range(2, min(i, K) + 1):
                solver.add_clause([r[i - 1][j - 1], -r[i][j]])

        # (6)  x_i ∨ r(i-1,j-1) ∨ ¬r(i,j)
        for i in range(2, num_frequency + 1):
            for j in range(1, min(i - 1, K) + 1):
                solver.add_clause([x[l][i], r[i - 1][j], -r[i][j]])

        # (7)  ¬x_i ∨ ¬r(i-1,K)
        for i in range(K + 1, num_frequency + 1):
            solver.add_clause([-x[l][i], -r[i - 1][K]])

        # (8)
        solver.add_clause([r[num_frequency-1][K], x[l][num_frequency]])
        solver.add_clause([r[num_frequency-1][K], r[num_frequency-1][K-1]])

def create_order_var(solver, num_cells, UB, top, x):
    g = [[0] * (UB + 1) for _ in range(num_cells + 1)]
    
    for i in range(1, num_cells + 1):
        for j in range(1, UB + 1):
            top += 1
            g[i][j] = top

    for i in range(1, num_cells + 1):
        for j in range(1, UB + 1):
            solver.add_clause([-x[i][j], g[i][j]])  # (3) x[i][j] => g[i][j]

    for i in range(1, num_cells + 1):
        for j in range(2, UB + 1):
            solver.add_clause([-g[i][j], g[i][j - 1]])  # (4) g[i][j] => g[i][j - 1]

    return  g, top

def add_distance_constraints(solver, num_cells, UB, x, matrix):
    for u in range(1, num_cells + 1):
        for v in range(u, num_cells + 1):
            d = matrix[u][v]
            if d > 0:
                for j in range(1, UB + 1):
                    for k in range(max(1, j - d + 1), min(UB, j + d - 1) + 1):
                        if u == v and j == k:
                            continue
                        solver.add_clause([-x[u][j], -x[v][k]])  # (5) x[u][j] => (-g[v][k] OR -l[v][k])

def create_frequency_constraints(solver, num_cells, UB, x, top):
    f = [0] * (UB + 1)
    for j in range(1, UB + 1):
        top += 1
        f[j] = top

    for i in range(1, num_cells + 1):
        for j in range(1, UB + 1):
            solver.add_clause([-x[i][j], f[j]])  # (6) x[i][j] => f[j]

    return f, top

def symmetry_breaking(solver, num_cells, x, demand_vector, matrix):
    clause = []
    for i in range(1, num_cells + 1):
        clause.append(x[i][1])  # Yêu cầu ít nhất phải sử dụng tần số 1
    solver.add_clause(clause)

    

def greedy(num_cells, demand, distance_matrix):
   
    assignment = {i: [] for i in range(1, num_cells + 1)}
    
    sorted_cells = sorted(range(1, num_cells + 1), key=lambda x: demand[x], reverse=True)
    
    for cell in sorted_cells:
        for _ in range(demand[cell]):
            freq = 1  # Tần số bắt đầu thử vẫn là 1
            
            while True:
                has_conflict = False
                
                # Kiểm tra nhiễu Co-site (d_ii)
                co_site_dist = distance_matrix[cell][cell]
                for used_f in assignment[cell]:
                    if abs(freq - used_f) < co_site_dist:
                        has_conflict = True
                        break
                
                # Kiểm tra nhiễu Inter-site (d_ij)
                if not has_conflict:
                    # Vòng lặp các trạm lân cận cũng chạy từ 1 đến num_cells
                    for other_cell in range(1, num_cells + 1):
                        if other_cell == cell or not assignment[other_cell]:
                            continue
                        
                        inter_site_dist = distance_matrix[cell][other_cell]
                        if inter_site_dist > 0:
                            for used_f in assignment[other_cell]:
                                if abs(freq - used_f) < inter_site_dist:
                                    has_conflict = True
                                    break
                        
                        if has_conflict:
                            break
                
                # Tăng tần số nếu có xung đột, ngược lại chốt gán
                if has_conflict:
                    freq += 1
                else:
                    assignment[cell].append(freq)
                    break
                    
    # Tìm Max Freq (UB) an toàn, tránh lỗi nếu đồ thị rỗng
    max_freq = 0
    min_freq = 10000
    for freqs in assignment.values():
        if freqs:
            max_freq = max(max_freq, max(freqs))
            min_freq = min(min_freq, min(freqs))
            
    return max_freq, min_freq, assignment

def greedy_plus(num_cells, demand, distance_matrix):
    assignment = {i: [] for i in range(1, num_cells + 1)}
    
    # --- CẢI TIẾN 1: TÍNH ĐIỂM ĐỘ KHÓ ĐỂ SẮP XẾP ---
    node_scores = {}
    for i in range(1, num_cells + 1):
        # Tổng các ràng buộc khoảng cách với các node khác
        inter_weight = sum(distance_matrix[i][j] for j in range(1, num_cells + 1) if j != i)
        co_site_weight = distance_matrix[i][i]
        
        # Trọng số = Demand * (Tổng ràng buộc Inter-site + Ràng buộc Co-site)
        node_scores[i] = demand[i] * (inter_weight + co_site_weight)
        
    # Sắp xếp giảm dần theo điểm độ khó
    sorted_cells = sorted(range(1, num_cells + 1), key=lambda x: node_scores[x], reverse=True)
    
    # --- BẮT ĐẦU GÁN TẦN SỐ ---
    for cell in sorted_cells:
        for _ in range(demand[cell]):
            freq = 1  
            
            while True:
                conflict_found = False
                
                # 1. Kiểm tra nhiễu Co-site (d_ii)
                co_site_dist = distance_matrix[cell][cell]
                for used_f in assignment[cell]:
                    if abs(freq - used_f) < co_site_dist:
                        # --- CẢI TIẾN 2: BƯỚC NHẢY TẦN SỐ ---
                        # Nhảy thẳng ra khỏi vùng cấm của used_f
                        freq = used_f + co_site_dist 
                        conflict_found = True
                        break
                        
                if conflict_found:
                    continue # Bắt đầu check lại từ đầu với freq mới
                
                # 2. Kiểm tra nhiễu Inter-site (d_ij)
                for other_cell in range(1, num_cells + 1):
                    if other_cell == cell or not assignment[other_cell]:
                        continue
                        
                    inter_site_dist = distance_matrix[cell][other_cell]
                    if inter_site_dist > 0:
                        for used_f in assignment[other_cell]:
                            if abs(freq - used_f) < inter_site_dist:
                                # Nhảy vọt qua vùng cấm inter-site
                                freq = used_f + inter_site_dist
                                conflict_found = True
                                break # Thoát vòng lặp used_f
                                
                    if conflict_found:
                        break # Thoát vòng lặp other_cell
                
                # Nếu không có bất kỳ xung đột nào, chốt tần số!
                if not conflict_found:
                    assignment[cell].append(freq)
                    break
                    
    # Tìm Max Freq và Min Freq
    max_freq = 0
    min_freq = float('inf')
    for freqs in assignment.values():
        if freqs:
            max_freq = max(max_freq, max(freqs))
            min_freq = min(min_freq, min(freqs))
            
    # Nếu đồ thị rỗng (min_freq không đổi) thì trả về 0
    if min_freq == float('inf'):
        min_freq = 0
            
    return max_freq, min_freq, assignment

def multi_greedy(num_cells, demand, distance_matrix, num_iterations=100):
    best_max_freq = float('inf')
    best_min_freq = 0
    best_assignment = None
    best_span = float('inf')
    
    # 1. Tính điểm độ khó gốc cho từng cell (Tư tưởng thuật toán F/DR)
    base_scores = {}
    for i in range(1, num_cells + 1):
        # Tổng tất cả các ràng buộc khoảng cách liên quan đến trạm i (Co-site + Inter-site)
        total_interference = sum(distance_matrix[i])
        base_scores[i] = demand[i] * total_interference
        
    # 2. Chạy Greedy nhiều lần để tìm UB (Span) ép sát nhất
    for iteration in range(num_iterations):
        assignment = {i: [] for i in range(1, num_cells + 1)}
        
        # Thêm nhiễu ngẫu nhiên (±10%) vào điểm gốc để sinh ra thứ tự ưu tiên mới
        current_scores = {i: base_scores[i] * random.uniform(0.9, 1.1) for i in range(1, num_cells + 1)}
        
        # Sắp xếp các cell theo điểm độ khó đã được xáo trộn nhẹ
        sorted_cells = sorted(range(1, num_cells + 1), key=lambda x: current_scores[x], reverse=True)
        
        # --- Giữ nguyên 100% logic gán tần số an toàn của bạn ---
        for cell in sorted_cells:
            for _ in range(demand[cell]):
                freq = 1  
                
                while True:
                    has_conflict = False
                    
                    # Kiểm tra nhiễu Co-site
                    co_site_dist = distance_matrix[cell][cell]
                    for used_f in assignment[cell]:
                        if abs(freq - used_f) < co_site_dist:
                            has_conflict = True
                            break
                    
                    # Kiểm tra nhiễu Inter-site
                    if not has_conflict:
                        for other_cell in range(1, num_cells + 1):
                            if other_cell == cell or not assignment[other_cell]:
                                continue
                            
                            inter_site_dist = distance_matrix[cell][other_cell]
                            if inter_site_dist > 0:
                                for used_f in assignment[other_cell]:
                                    if abs(freq - used_f) < inter_site_dist:
                                        has_conflict = True
                                        break
                            if has_conflict:
                                break
                    
                    if has_conflict:
                        freq += 1
                    else:
                        assignment[cell].append(freq)
                        break
                        
        # 3. Tính Span của cấu hình vừa chạy xong
        max_f = 0
        min_f = float('inf')
        for freqs in assignment.values():
            if freqs:
                max_f = max(max_f, max(freqs))
                min_f = min(min_f, min(freqs))
                
        if min_f == float('inf'): min_f = 0
        current_span = max_f - min_f
        
        # 4. Nếu tìm được Span nhỏ hơn, chốt làm UB tốt nhất
        if current_span < best_span:
            best_span = current_span
            best_max_freq = max_f
            best_min_freq = min_f
            best_assignment = assignment
            
    return best_max_freq, best_min_freq, best_assignment

def solve_and_print(solver, num_cells, UB, x, demand_vector, matrix):
    span = -1
    assignment = None
    if solver.solve():
        model = solver.get_model()
        assignment = {i: [] for i in range(1, num_cells + 1)}
        
        
        for i in range(1, num_cells + 1):
            for j in range(1, UB + 1):
                if model[x[i][j] - 1] > 0:
                    assignment[i].append(j)
        max_freq = 0
        min_freq = 10000
        for freqs in assignment.values():
            if freqs:
                max_freq = max(max_freq, max(freqs))
                min_freq = min(min_freq, min(freqs))
        
        if max_freq < min_freq:
            raise ValueError("Invalid frequency assignment: max_freq < min_freq")
        span = max_freq - min_freq
        print(f"Span: {span} ({max_freq}-{min_freq})")
    else:
        print("No solution found.")
    return span, assignment,

def verify_solution(assignment, demand_vector, distance_matrix):
    for cell, freqs in assignment.items():
        if len(freqs) != demand_vector[cell]:
            print(f"Cell {cell} has {len(freqs)} frequencies assigned, but demand is {demand_vector[cell]}.")
            return False
        # Kiểm tra nhiễu Co-site
        for i in range(len(freqs)):
            for j in range(i + 1, len(freqs)):
                if abs(freqs[i] - freqs[j]) < distance_matrix[cell][cell]:
                    print(f"Co-site interference in cell {cell} between frequencies {freqs[i]} and {freqs[j]} with distance {distance_matrix[cell][cell]}.")
                    return False
        
        # Kiểm tra nhiễu Inter-site
        for other_cell, other_freqs in assignment.items():
            if other_cell == cell:
                continue
            
            inter_site_dist = distance_matrix[cell][other_cell]
            if inter_site_dist > 0:
                for f1 in freqs:
                    for f2 in other_freqs:
                        if abs(f1 - f2) < inter_site_dist:
                            print(f"Inter-site interference between cell {cell} (freq {f1}) and cell {other_cell} (freq {f2}) with distance {inter_site_dist}.")
                            return False
    return True
if __name__ == "__main__":
    start_time = time.perf_counter()

    dataset = sys.argv[1]
    file_path = f"dataset/{dataset}.txt"

    num_cells, demand_vector, matrix = read_dataset(file_path)
    # max_fre, min_fre, greedy_assignment = greedy(num_cells, demand_vector, matrix)
    # max_fre, min_fre, greedy_assignment = greedy_plus(num_cells, demand_vector, matrix)
    max_fre, min_fre, greedy_assignment = multi_greedy(num_cells, demand_vector, matrix, num_iterations=100)
    print(f"Greedy span: {max_fre - min_fre} ({max_fre}-{min_fre})")
    if verify_solution(greedy_assignment, demand_vector, matrix):
        print("Greedy solution is valid.")
    else:
        print("Greedy solution is invalid.")

    solver = Solver(name='cadical195')

    UB = max_fre - 1  # Giảm UB ban đầu để bắt đầu từ UB - 1
    x, top = create_frequency_var(num_cells, UB)
    
    add_distance_constraints(solver, num_cells, UB, x, matrix)
    f, top = create_frequency_constraints(solver, num_cells, UB, x, top)

    # add exactly k constraints cuối cùng vì không trả về top_id
    add_exactly_k_constraints(solver, num_cells, UB, x, demand_vector, top)
    # add_exactly_k_nsc(solver, num_cells, UB, x, demand_vector, top)
    # symmetry_breaking(solver, num_cells, x, demand_vector, matrix)

    solver.add_clause([f[1]])
    while True:
        print("--------------------------------")
        print(f"Trying with UB = {UB}...")
        span, assignment = solve_and_print(solver, num_cells, UB, x, demand_vector, matrix)
        if assignment:
            print(f"Time taken: {time.perf_counter() - start_time:.2f}s")
            if verify_solution(assignment, demand_vector, matrix):
                print("Solution is valid.")
            else:
                print("Solution is invalid.")
                break
            for i in range(span + 1, UB + 1):
                solver.add_clause([-f[i]])  # Ràng buộc mới: f[i] = 0 cho i >= span
            UB = span  # Cập nhật UB mới dựa trên span tìm được
        else:
            print(f"Optimal span found: {UB}")
            print(f"Time taken: {time.perf_counter() - start_time:.2f}s")
            break