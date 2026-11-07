package com.psi.training.nexacro.xapi.api.service;

import com.nexacro.java.xapi.data.DataSet;
import com.psi.training.nexacro.xapi.api.mapper.EmployeeMapper;
import com.psi.training.nexacro.xapi.common.NexacroConvert;
import com.psi.training.nexacro.xapi.entity.entity.EmployeeEntity;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
public class EmployeeService {
    @Autowired
    private EmployeeMapper employeeMapper;

    public List<Map<String, String>> getAll(Map<String, String> data) {
        List<Map<String, String>> rows = new ArrayList<>();
        EmployeeEntity employeeEntity = new EmployeeEntity();

        // Màn hình gửi điều kiện tìm ở cột "id" của dsInput; rỗng thì lấy tất cả
        if (data != null) {
            employeeEntity.setEmployeeId(data.get("id"));
        }

        List<EmployeeEntity> employeeEntities = employeeMapper.getAll(employeeEntity);

        for (EmployeeEntity employee : employeeEntities) {
            Map<String, String> row = NexacroConvert.convertObjectToMap(employee);
            rows.add(row);
        }

        return rows;
    }

    @Transactional
    public void save(DataSet dataSet) {
        // Nexacro gửi kèm RowType của từng dòng khi inData có ":U"
        for (int i = 0; i < dataSet.getRowCount(); i++) {
            EmployeeEntity employee = NexacroConvert.convertMapToObject(dataSet.getRowToMap(i), EmployeeEntity.class);

            if (dataSet.getRowType(i) == DataSet.ROW_TYPE_INSERTED) {
                employeeMapper.insert(employee);
            } else if (dataSet.getRowType(i) == DataSet.ROW_TYPE_UPDATED) {
                employeeMapper.update(employee);
            }
        }

        // Dòng bị xóa không nằm trong getRowCount() mà nằm ở danh sách removed
        for (int i = 0; i < dataSet.getRemovedRowCount(); i++) {
            employeeMapper.delete(dataSet.getRemovedStringData(i, "employeeId"));
        }
    }
}
