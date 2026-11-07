package com.psi.training.nexacro.xapi.entity.response;

import java.util.List;
import java.util.Map;

public class Dataset {
    private String id;
    private List<ColumnEntity> columns;
    private List<Map<String,String>> rows;

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public List<ColumnEntity> getColumns() {
        return columns;
    }

    public void setColumns(List<ColumnEntity> columns) {
        this.columns = columns;
    }

    public List<Map<String, String>> getRows() {
        return rows;
    }

    public void setRows(List<Map<String, String>> rows) {
        this.rows = rows;
    }
}
