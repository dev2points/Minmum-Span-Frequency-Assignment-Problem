import sys
import time
from pysat.solvers import Solver
from pysat.card import CardEnc


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
            enc = CardEnc.equals(lits=vars_for_cell, bound=k, top_id=top, encoding=1)
            for clause in enc.clauses:
                solver.add_clause(clause)
            if enc.clauses:
                top = max(top, enc.nv)

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
    degrees = [0] * (num_cells + 1)
    for i in range(1, num_cells + 1):
        degrees[i] = sum(matrix[i][j] for j in range(1, num_cells + 1)) + demand_vector[i]

    max = 1
    for i in range(2, num_cells + 1):
        if degrees[i] > degrees[max]:
            max = i

    solver.add_clause([x[max][1]])  # (7) x[max][1] = 1

    

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
    for freqs in assignment.values():
        if freqs:
            max_freq = max(max_freq, max(freqs))
            
    return max_freq, assignment

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
        if verify_solution(assignment, demand_vector, matrix):
            print("Solution is valid.")
        else:
            print("Solution is invalid.")
    else:
        print("No solution found.")
    return span, assignment

def verify_solution(assignment, demand_vector, distance_matrix):
    for cell, freqs in assignment.items():
        if len(freqs) != demand_vector[cell]:
            return False
        # Kiểm tra nhiễu Co-site
        for i in range(len(freqs)):
            for j in range(i + 1, len(freqs)):
                if abs(freqs[i] - freqs[j]) < distance_matrix[cell][cell]:
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
                            return False
    return True
if __name__ == "__main__":
    start_time = time.perf_counter()

    dataset = sys.argv[1]
    file_path = f"dataset/{dataset}.txt"

    num_cells, demand_vector, matrix = read_dataset(file_path)
    UB, greedy_assignment = greedy(num_cells, demand_vector, matrix)
    print(f"Greedy UB: {UB}")
    if verify_solution(greedy_assignment, demand_vector, matrix):
        print("Greedy solution is valid.")
    else:
        print("Greedy solution is invalid.")

    solver = Solver(name='cadical195')

    UB -= 1  # Giảm UB ban đầu để bắt đầu từ UB - 1
    x, top = create_frequency_var(num_cells, UB)
    # l, g, top = create_order_var(solver, num_cells, UB, top, x)
    add_distance_constraints(solver, num_cells, UB, x, matrix)
    f, top = create_frequency_constraints(solver, num_cells, UB, x, top)
    # add exactly k constraints cuối cùng vì không trả về top_id
    add_exactly_k_constraints(solver, num_cells, UB, x, demand_vector, top)
    symmetry_breaking(solver, num_cells, x, demand_vector, matrix)

    solver.add_clause([f[1]])
    while True:
        print("--------------------------------")
        print(f"Trying with UB = {UB}...")
        span, assignment = solve_and_print(solver, num_cells, UB, x, demand_vector, matrix)
        if assignment:
            print(f"Time taken: {time.perf_counter() - start_time:.2f}s")

            for i in range(span + 1, UB + 1):
                solver.add_clause([-f[i]])  # Ràng buộc mới: f[i] = 0 cho i >= span
            UB = span  # Cập nhật UB mới dựa trên span tìm được
        else:
            print(f"Optimal span found: {UB}")
            print(f"Time taken: {time.perf_counter() - start_time:.2f}s")
            break