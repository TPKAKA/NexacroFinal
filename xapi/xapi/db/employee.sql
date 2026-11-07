-- ==========================================
-- EMPLOYEE DEMO DATABASE SCRIPT
-- PostgreSQL
-- ==========================================

DROP TABLE IF EXISTS employee;

CREATE TABLE employee (
    employee_id     BIGSERIAL PRIMARY KEY,
    employee_code   VARCHAR(20) NOT NULL UNIQUE,
    full_name       VARCHAR(200) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    phone_number    VARCHAR(20),
    gender          CHAR(1),
    birth_date      DATE,
    department      VARCHAR(100),
    position        VARCHAR(100),
    salary          NUMERIC(15,2),
    hire_date       DATE NOT NULL,
    resign_date     DATE,
    status          VARCHAR(20) DEFAULT 'ACTIVE',
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_employee_hire_date ON employee(hire_date);
CREATE INDEX idx_employee_created_at ON employee(created_at);
CREATE INDEX idx_employee_department ON employee(department);
CREATE INDEX idx_employee_status ON employee(status);

INSERT INTO employee (
employee_code,full_name,email,phone_number,gender,birth_date,
department,position,salary,hire_date,resign_date,status,created_at,updated_at
)
VALUES
('EMP001','Nguyen Van A','nguyenvana@example.com','0901234567','M','1995-05-12','IT','Developer',20000000,'2023-01-15',NULL,'ACTIVE','2023-01-15 08:30:00',CURRENT_TIMESTAMP),
('EMP002','Tran Thi B','tranthib@example.com','0901234568','F','1997-08-20','HR','HR Executive',15000000,'2023-03-10',NULL,'ACTIVE','2023-03-10 09:00:00',CURRENT_TIMESTAMP),
('EMP003','Le Van C','levanc@example.com','0901234569','M','1994-11-02','IT','Tester',18000000,'2023-06-05',NULL,'ACTIVE','2023-06-05 10:15:00',CURRENT_TIMESTAMP),
('EMP004','Pham Thi D','phamthid@example.com','0901234570','F','1998-01-25','Finance','Accountant',17000000,'2024-01-08',NULL,'ACTIVE','2024-01-08 08:45:00',CURRENT_TIMESTAMP),
('EMP005','Hoang Van E','hoangvane@example.com','0901234571','M','1992-09-15','IT','Tech Lead',35000000,'2022-07-01',NULL,'ACTIVE','2022-07-01 08:00:00',CURRENT_TIMESTAMP),
('EMP006','Vo Thi F','vothif@example.com','0901234572','F','1996-12-10','Marketing','Marketing Executive',16000000,'2024-03-12',NULL,'ACTIVE','2024-03-12 09:30:00',CURRENT_TIMESTAMP),
('EMP007','Do Van G','dovang@example.com','0901234573','M','1989-04-18','Sales','Sales Manager',30000000,'2021-11-01',NULL,'ACTIVE','2021-11-01 08:00:00',CURRENT_TIMESTAMP),
('EMP008','Bui Thi H','buithih@example.com','0901234574','F','1999-07-07','IT','Intern',8000000,'2025-01-06',NULL,'ACTIVE','2025-01-06 08:30:00',CURRENT_TIMESTAMP),
('EMP009','Nguyen Van I','nguyenvani@example.com','0901234575','M','1990-03-05','IT','Project Manager',40000000,'2020-04-20',NULL,'ACTIVE','2020-04-20 08:00:00',CURRENT_TIMESTAMP),
('EMP010','Tran Thi K','tranthik@example.com','0901234576','F','1993-10-30','IT','Business Analyst',22000000,'2023-09-01',NULL,'ACTIVE','2023-09-01 08:15:00',CURRENT_TIMESTAMP);
